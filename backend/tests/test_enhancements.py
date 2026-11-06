import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from backend.app.models import db, Shop, User, Customer, CustomerSession, CustomerQuestion, Conversation, Message, AnswerFeedback, KnowledgeBase
from backend.app.services.ai_service import AIService, sanitize_customer_answer, FALLBACK_MESSAGE
from backend.app.services.email_inbound_service import EmailInboundService
from backend.app.services.email_sync_service import EmailSyncService

# Helper to register and login an owner
def _setup_owner_and_shop(client, slug="enh-shop", email="enh_owner@test.com"):
    res = client.post("/api/auth/register", json={
        "full_name": "Enhancement Owner",
        "email": email,
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Enhancement Shop",
        "slug": slug
    })
    token = res.get_json()["data"]["token"]
    shop = res.get_json()["data"]["shop"]
    return {"Authorization": f"Bearer {token}"}, shop

# ----------------------------------------------------------------------
# FEATURE 2: CUSTOMER ANSWER FEEDBACK TESTS
# ----------------------------------------------------------------------
def test_feedback_01_customer_good_answer_submission(client, app):
    headers, shop = _setup_owner_and_shop(client, "shop-fb-1", "owner_fb1@test.com")

    # Add knowledge
    client.post("/api/knowledge", json={
        "title": "Return Policy", "content": "You can return items within 30 days.", "category": "Policy"
    }, headers=headers)

    # Customer creates session & asks question
    sess = client.post("/api/public/shop/shop-fb-1/session", json={
        "first_name": "John", "last_name": "Tester", "email": "john@test.com"
    }).get_json()["data"]["session_token"]

    chat_res = client.post("/api/public/shop/shop-fb-1/chat", json={
        "message": "What is your return policy?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat_res.get_json()["data"]["question_id"]
    assert chat_res.get_json()["data"]["can_answer"] is True

    # Customer submits Good feedback
    fb_res = client.post("/api/public/shop/shop-fb-1/feedback", json={
        "question_id": q_id,
        "feedback_type": "good"
    }, headers={"X-Customer-Session": sess})

    assert fb_res.status_code == 200
    assert fb_res.get_json()["data"]["feedback_type"] == "good"
    assert "Thanks for your feedback" in fb_res.get_json()["message"]

    # Verify saved in database
    with app.app_context():
        fb = AnswerFeedback.query.filter_by(customer_question_id=q_id).first()
        assert fb is not None
        assert fb.feedback_type == "good"

def test_feedback_02_customer_bad_answer_with_comment(client, app):
    headers, shop = _setup_owner_and_shop(client, "shop-fb-2", "owner_fb2@test.com")

    client.post("/api/knowledge", json={
        "title": "Store Hours", "content": "Open Monday to Friday 9 AM to 6 PM.", "category": "Hours"
    }, headers=headers)

    sess = client.post("/api/public/shop/shop-fb-2/session", json={
        "first_name": "Sarah", "last_name": "Connor", "email": "sarah@resistance.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/shop-fb-2/chat", json={
        "message": "What are your open hours?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # Customer clicks Bad Answer with optional comment
    fb_res = client.post("/api/public/shop/shop-fb-2/feedback", json={
        "question_id": q_id,
        "feedback_type": "bad",
        "comment": "Does not say if you are open on weekends."
    }, headers={"X-Customer-Session": sess})

    assert fb_res.status_code == 200
    assert fb_res.get_json()["data"]["feedback_type"] == "bad"

    with app.app_context():
        fb = AnswerFeedback.query.filter_by(customer_question_id=q_id).first()
        assert fb.feedback_type == "bad"
        assert fb.reason == "Does not say if you are open on weekends."

def test_feedback_03_dashboard_counters_update_correctly(client):
    headers, shop = _setup_owner_and_shop(client, "shop-fb-3", "owner_fb3@test.com")

    client.post("/api/knowledge", json={
        "title": "Products", "content": "We sell smartphones and laptops.", "category": "Products"
    }, headers=headers)

    sess = client.post("/api/public/shop/shop-fb-3/session", json={
        "first_name": "Tony", "last_name": "Stark", "email": "tony@stark.com"
    }).get_json()["data"]["session_token"]

    # Ask 2 questions
    q1 = client.post("/api/public/shop/shop-fb-3/chat", json={
        "message": "Do you sell laptops?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    q2 = client.post("/api/public/shop/shop-fb-3/chat", json={
        "message": "Do you sell smartphones?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    # Q1 -> Good, Q2 -> Bad
    client.post("/api/public/shop/shop-fb-3/feedback", json={
        "question_id": q1, "feedback_type": "good"
    }, headers={"X-Customer-Session": sess})

    client.post("/api/public/shop/shop-fb-3/feedback", json={
        "question_id": q2, "feedback_type": "bad", "comment": "Need brand details"
    }, headers={"X-Customer-Session": sess})

    # Verify dashboard stats
    stats_res = client.get("/api/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.get_json()["data"]["stats"]
    assert stats["good_answers"] == 1
    assert stats["bad_answers"] == 1

    # Verify feedback list endpoint returns computed percentage
    fb_list = client.get("/api/feedback", headers=headers).get_json()["data"]
    assert fb_list["total_good"] == 1
    assert fb_list["total_bad"] == 1
    assert fb_list["good_percentage"] == 50.0

def test_feedback_04_feedback_duplicate_or_update(client, app):
    headers, shop = _setup_owner_and_shop(client, "shop-fb-4", "owner_fb4@test.com")

    client.post("/api/knowledge", json={
        "title": "Delivery", "content": "We offer home delivery within city.", "category": "Delivery"
    }, headers=headers)

    sess = client.post("/api/public/shop/shop-fb-4/session", json={
        "first_name": "Peter", "last_name": "Parker", "email": "peter@dailybugle.com"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-fb-4/chat", json={
        "message": "Do you deliver?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    # Initial rating: bad
    client.post("/api/public/shop/shop-fb-4/feedback", json={
        "question_id": q_id, "feedback_type": "bad"
    }, headers={"X-Customer-Session": sess})

    # Customer changes rating to good
    client.post("/api/public/shop/shop-fb-4/feedback", json={
        "question_id": q_id, "feedback_type": "good"
    }, headers={"X-Customer-Session": sess})

    with app.app_context():
        feedbacks = AnswerFeedback.query.filter_by(customer_question_id=q_id).all()
        # Should be updated, not duplicated
        assert len(feedbacks) == 1
        assert feedbacks[0].feedback_type == "good"

def test_feedback_05_owner_correction_added_to_knowledge_base(client, app):
    headers, shop = _setup_owner_and_shop(client, "shop-fb-5", "owner_fb5@test.com")

    client.post("/api/knowledge", json={
        "title": "Returns", "content": "Returns with bill.", "category": "Policy"
    }, headers=headers)

    sess = client.post("/api/public/shop/shop-fb-5/session", json={
        "first_name": "Bruce", "last_name": "Banner", "email": "bruce@avengers.com"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-fb-5/chat", json={
        "message": "Can I return without tags?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    # Customer marks bad
    client.post("/api/public/shop/shop-fb-5/feedback", json={
        "question_id": q_id, "feedback_type": "bad", "comment": "Vague on tags"
    }, headers={"X-Customer-Session": sess})

    # Owner reviews and submits verified correction
    corr_res = client.post(f"/api/feedback/{q_id}/bad", json={
        "reason": "Clarified tag requirement",
        "correct_answer": "No, all returns must have the original retail tags attached."
    }, headers=headers)

    assert corr_res.status_code == 200
    with app.app_context():
        kb = KnowledgeBase.query.filter_by(shop_id=shop["id"], source_type="feedback_correction").first()
        assert kb is not None
        assert "retail tags attached" in kb.content

def test_feedback_06_tenant_isolation_on_feedback(client):
    headers_a, shop_a = _setup_owner_and_shop(client, "shop-fb-6a", "owner6a@test.com")
    headers_b, shop_b = _setup_owner_and_shop(client, "shop-fb-6b", "owner6b@test.com")

    client.post("/api/knowledge", json={
        "title": "About A", "content": "Shop A sells organic food.", "category": "General"
    }, headers=headers_a)

    sess_a = client.post("/api/public/shop/shop-fb-6a/session", json={
        "first_name": "Cust", "last_name": "A", "email": "cust_a@test.com"
    }).get_json()["data"]["session_token"]

    q_a = client.post("/api/public/shop/shop-fb-6a/chat", json={
        "message": "Do you sell food?"
    }, headers={"X-Customer-Session": sess_a}).get_json()["data"]["question_id"]

    # Customer from Shop B attempts to rate Shop A's question -> Must be rejected 404
    sess_b = client.post("/api/public/shop/shop-fb-6b/session", json={
        "first_name": "Cust", "last_name": "B", "email": "cust_b@test.com"
    }).get_json()["data"]["session_token"]

    cross_res = client.post("/api/public/shop/shop-fb-6b/feedback", json={
        "question_id": q_a,
        "feedback_type": "good"
    }, headers={"X-Customer-Session": sess_b})

    assert cross_res.status_code == 404

# ----------------------------------------------------------------------
# FEATURE 1: TWO-WAY EMAIL COMMUNICATION TESTS
# ----------------------------------------------------------------------
def test_two_way_email_01_inbound_reply_webhook_matched(client, app):
    headers, shop = _setup_owner_and_shop(client, "shop-email-1", "owner_em1@test.com")

    # Customer asks question that is marked pending
    sess = client.post("/api/public/shop/shop-email-1/session", json={
        "first_name": "Wanda", "last_name": "Maximoff", "email": "wanda@westview.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/shop-email-1/chat", json={
        "message": "Do you customize vintage cameras?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # Owner answers question
    mock_smtp_res = {"success": True, "status": "sent", "error": None, "provider": "mock"}
    with patch("backend.app.services.email_service.EmailService.send_customer_answer_email", return_value=mock_smtp_res):
        client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, our technicians specialize in vintage Leica and Canon restoration."
        }, headers=headers)

    # Customer replies to email notification
    inbound_payload = {
        "from": "wanda@westview.com",
        "to": "support@shopgenie.local",
        "subject": f"Re: Your Question Has Been Answered – Enhancement Shop [Ref: #SG-{q_id}]",
        "text": """That is fantastic! How long does a full CLA restoration typically take?

--- Please reply above this line to respond to Enhancement Shop [Ref: #SG-""" + str(q_id) + """] ---
On Mon, Nov 6, 2026, Enhancement Shop wrote:
> Yes, our technicians specialize in vintage Leica and Canon restoration.
"""
    }

    inbound_res = client.post("/api/email/inbound", json=inbound_payload)
    assert inbound_res.status_code == 200
    data = inbound_res.get_json()["data"]
    assert data["status"] == "processed"
    assert data["question_id"] == q_id
    assert "How long does a full CLA restoration" in data["reply_content"]

    # Verify question status is customer_replied in database
    with app.app_context():
        q = db.session.get(CustomerQuestion, q_id)
        assert q.status == "customer_replied"

def test_two_way_email_02_customer_reply_appears_in_owner_thread(client):
    headers, shop = _setup_owner_and_shop(client, "shop-email-2", "owner_em2@test.com")

    sess = client.post("/api/public/shop/shop-email-2/session", json={
        "first_name": "Natasha", "last_name": "Romanoff", "email": "natasha@shield.gov"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-email-2/chat", json={
        "message": "Do you stock Kevlar jackets?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    mock_res = {"success": True, "status": "sent", "error": None, "provider": "mock"}
    with patch("backend.app.services.email_service.EmailService.send_customer_answer_email", return_value=mock_res):
        client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "We have Level II and Level III lightweight tactical vests."
        }, headers=headers)

    # Inbound email arrives
    client.post("/api/email/inbound", json={
        "from": "natasha@shield.gov",
        "to": "support@shopgenie.local",
        "subject": f"Re: [Ref: #SG-{q_id}] Tactical vest inquiry",
        "text": "Can I inspect them at the store tomorrow morning?"
    })

    # Owner views question details
    q_details = client.get(f"/api/questions/{q_id}", headers=headers).get_json()["data"]
    assert q_details["status"] == "customer_replied"
    assert len(q_details["messages"]) >= 3
    # Check that customer's reply is present in messages thread
    customer_replies = [m for m in q_details["messages"] if m["sender_type"] == "customer"]
    assert any("inspect them at the store tomorrow" in m["message_content"] for m in customer_replies)

def test_two_way_email_03_owner_sends_follow_up_and_customer_notified(client):
    headers, shop = _setup_owner_and_shop(client, "shop-email-3", "owner_em3@test.com")

    sess = client.post("/api/public/shop/shop-email-3/session", json={
        "first_name": "Stephen", "last_name": "Strange", "email": "stephen@kamar-taj.org"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-email-3/chat", json={
        "message": "Do you sell antique Sanskrit manuscripts?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    mock_res = {"success": True, "status": "sent", "error": None, "provider": "mock"}
    with patch("backend.app.services.email_service.EmailService.send_customer_answer_email", return_value=mock_res):
        client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "We have a curated collection of rare 18th-century manuscripts."
        }, headers=headers)

    # Customer replies
    client.post("/api/email/inbound", json={
        "from": "stephen@kamar-taj.org",
        "to": "support@shopgenie.local",
        "subject": f"Re: [Ref: #SG-{q_id}] Rare manuscripts",
        "text": "Are they available for private viewing?"
    })

    # Owner sends follow-up response
    with patch("backend.app.services.email_service.EmailService.send_customer_answer_email", return_value=mock_res) as mock_send:
        follow_up_res = client.post(f"/api/questions/{q_id}/follow-up", json={
            "reply": "Yes, private viewings are available by appointment on Thursdays."
        }, headers=headers)

        assert follow_up_res.status_code == 200
        assert follow_up_res.get_json()["data"]["question"]["status"] == "answered"
        assert mock_send.called
        kwargs = mock_send.call_args[1]
        assert kwargs["is_follow_up"] is True
        assert kwargs["customer_email"] == "stephen@kamar-taj.org"
        assert "private viewings are available" in kwargs["answer"]

def test_two_way_email_04_duplicate_inbound_email_prevented(client):
    headers, shop = _setup_owner_and_shop(client, "shop-email-4", "owner_em4@test.com")

    sess = client.post("/api/public/shop/shop-email-4/session", json={
        "first_name": "Carol", "last_name": "Danvers", "email": "carol@space.com"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-email-4/chat", json={
        "message": "Do you ship interplanetary?"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    mock_res = {"success": True, "status": "sent", "error": None, "provider": "mock"}
    with patch("backend.app.services.email_service.EmailService.send_customer_answer_email", return_value=mock_res):
        client.post(f"/api/questions/{q_id}/answer", json={"answer": "Only within Earth orbit."}, headers=headers)

    msg_id_header = "<unique-msg-id-12345@mail.com>"
    payload = {
        "from": "carol@space.com",
        "to": "support@shopgenie.local",
        "subject": f"Re: [Ref: #SG-{q_id}] Shipping",
        "text": "Understood, thank you.",
        "message_id": msg_id_header
    }

    # 1st time -> processed
    res1 = client.post("/api/email/inbound", json=payload)
    assert res1.get_json()["data"]["status"] == "processed"

    # 2nd time with same message_id -> duplicate
    res2 = client.post("/api/email/inbound", json=payload)
    assert res2.status_code == 200
    assert res2.get_json()["data"]["status"] == "duplicate"

def test_two_way_email_05_unauthorized_sender_rejected(client):
    headers, shop = _setup_owner_and_shop(client, "shop-email-5", "owner_em5@test.com")

    sess = client.post("/api/public/shop/shop-email-5/session", json={
        "first_name": "Legitimate", "last_name": "Customer", "email": "legit@user.com"
    }).get_json()["data"]["session_token"]

    q_id = client.post("/api/public/shop/shop-email-5/chat", json={
        "message": "Order tracking"
    }, headers={"X-Customer-Session": sess}).get_json()["data"]["question_id"]

    # Hacker sends email attempting to hijack or reply to question #q_id
    spoof_res = client.post("/api/email/inbound", json={
        "from": "hacker@malicious.com",
        "to": "support@shopgenie.local",
        "subject": f"Re: [Ref: #SG-{q_id}] Order tracking",
        "text": "Change delivery address to Hacker Den."
    })

    assert spoof_res.status_code == 403
    assert "not authorized" in spoof_res.get_json()["message"]

def test_two_way_email_06_cross_shop_isolation(client):
    headers_a, shop_a = _setup_owner_and_shop(client, "shop-em-6a", "owner6a_em@test.com")
    headers_b, shop_b = _setup_owner_and_shop(client, "shop-em-6b", "owner6b_em@test.com")

    sess_a = client.post("/api/public/shop/shop-em-6a/session", json={
        "first_name": "Alice", "last_name": "A", "email": "alice_a@test.com"
    }).get_json()["data"]["session_token"]

    q_a = client.post("/api/public/shop/shop-em-6a/chat", json={
        "message": "Shop A Question"
    }, headers={"X-Customer-Session": sess_a}).get_json()["data"]["question_id"]

    # Owner B attempts to send follow-up to Shop A's question -> 404 unauthorized
    hack_res = client.post(f"/api/questions/{q_a}/follow-up", json={
        "reply": "Hijacked follow up"
    }, headers=headers_b)
    assert hack_res.status_code == 404

# ----------------------------------------------------------------------
# FEATURE 3: CHATBOT CLEAN ANSWER DISPLAY TESTS
# ----------------------------------------------------------------------
def test_chatbot_clean_answer_no_retrieval_metadata():
    raw_dirty_answer = "[Entry 1 - Customer FAQ] FAQ: yes i want to exchange an product Question: yes i want to exchange an product Answer: need bill and valid id proof"
    cleaned = sanitize_customer_answer(raw_dirty_answer, question="Can I exchange a product?")
    
    assert "[Entry 1" not in cleaned
    assert "FAQ:" not in cleaned
    assert "Question:" not in cleaned
    assert "Answer:" not in cleaned
    assert "bill and a valid ID proof" in cleaned

def test_chatbot_unknown_fallback_pending_workflow(client):
    headers, shop = _setup_owner_and_shop(client, "shop-clean-1", "owner_clean1@test.com")

    sess = client.post("/api/public/shop/shop-clean-1/session", json={
        "first_name": "Test", "last_name": "User", "email": "user@test.com"
    }).get_json()["data"]["session_token"]

    chat_res = client.post("/api/public/shop/shop-clean-1/chat", json={
        "message": "Can I travel faster than the speed of light in your store?"
    }, headers={"X-Customer-Session": sess})

    data = chat_res.get_json()["data"]
    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == FALLBACK_MESSAGE


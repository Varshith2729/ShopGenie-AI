import json
import pytest
from backend.app.models import db, Shop, CustomerQuestion, KnowledgeBase, Message, CustomerSession

@pytest.fixture
def shop_setup(client):
    """Register Shop A (Ravi Mobiles) with comprehensive knowledge base."""
    res_a = client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@ravimobiles.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles",
        "description": "We sell smartphones, mobile accessories, and gadgets."
    })
    token_a = res_a.get_json()["data"]["token"]
    shop_a_id = res_a.get_json()["data"]["shop"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Add Knowledge Entries to Shop A
    # 1. Opening hours
    client.post("/api/knowledge", json={
        "title": "Opening Hours",
        "content": "The shop opens every day at 10 AM and closes at 9 PM.",
        "category": "Timings"
    }, headers=headers_a)

    # 2. Location
    client.post("/api/knowledge", json={
        "title": "Shop Address",
        "content": "We are located at 45 MG Road, Near Metro Station, Bangalore.",
        "category": "Address"
    }, headers=headers_a)

    # 3. Products
    client.post("/api/knowledge", json={
        "title": "Available Smartphones",
        "content": "We sell Apple iPhone 15, Samsung Galaxy S24, and OnePlus 12 with full official warranty.",
        "category": "Products"
    }, headers=headers_a)

    # 4. Pricing
    client.post("/api/knowledge", json={
        "title": "iPhone 15 Pricing",
        "content": "The Apple iPhone 15 128GB is priced at Rs. 79,999.",
        "category": "Products"
    }, headers=headers_a)

    # 5. Return Policy
    client.post("/api/knowledge", json={
        "title": "Return and Exchange Policy",
        "content": "We offer a 7-day replacement policy for all mobile devices with original bill and box.",
        "category": "Policy"
    }, headers=headers_a)

    # Create Customer Session for Shop A
    sess_res = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "Arun",
        "last_name": "Kumar",
        "email": "arun@example.com"
    })
    cust_token = sess_res.get_json()["data"]["session_token"]

    return {
        "shop_a_id": shop_a_id,
        "token_a": token_a,
        "headers_a": headers_a,
        "cust_token": cust_token
    }

# ----------------------------------------------------------------------
# 1. Basic opening-hours question
# ----------------------------------------------------------------------
def test_01_basic_opening_hours_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "When does the shop open?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert "10 AM" in data["answer"]
    assert "reopen" not in data["answer"].lower() or "10 am" in data["answer"].lower()

# ----------------------------------------------------------------------
# 2. Rephrased opening-hours question
# ----------------------------------------------------------------------
def test_02_rephrased_opening_hours_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Shop opening time?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert "10 AM" in data["answer"]

# ----------------------------------------------------------------------
# 3. Reopen question ("When will the shop reopen?")
# ROOT CAUSE FIX VERIFICATION: Must answer 10 AM, not fallback
# ----------------------------------------------------------------------
def test_03_reopen_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "When will the shop reopen?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert "10 AM" in data["answer"]
    assert data["answer"] != "Thank you! The shop owner will reply to you soon by email."

# ----------------------------------------------------------------------
# 4. Follow-up question ("What about tomorrow?")
# ----------------------------------------------------------------------
def test_04_follow_up_question(client, shop_setup):
    # Turn 1: Ask when shop opens
    client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "When does the shop open?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})

    # Turn 2: Follow-up question relying on turn 1
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "What about tomorrow?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert "10 AM" in data["answer"] or "open" in data["answer"].lower()

# ----------------------------------------------------------------------
# 5. Shop location question
# ----------------------------------------------------------------------
def test_05_shop_location_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Where is the shop located?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert "MG Road" in data["answer"] or "Bangalore" in data["answer"]

# ----------------------------------------------------------------------
# 6. Product information question
# ----------------------------------------------------------------------
def test_06_product_information_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Do you have mobile phones?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert any(brand in data["answer"] for brand in ["iPhone", "Samsung", "OnePlus", "smartphones"])

# ----------------------------------------------------------------------
# 7. Price retrieval question
# ----------------------------------------------------------------------
def test_07_price_retrieval_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "How much does the iPhone 15 cost?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert "79,999" in data["answer"]

# ----------------------------------------------------------------------
# 8. Return policy question
# ----------------------------------------------------------------------
def test_08_return_policy_question(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "What is your return policy?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert "7-day" in data["answer"] or "replacement" in data["answer"].lower()

# ----------------------------------------------------------------------
# 9. Informal English ("u guys open at 10?")
# ----------------------------------------------------------------------
def test_09_informal_english(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "u guys open at 10?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert "10 AM" in data["answer"]

# ----------------------------------------------------------------------
# 10. Spelling mistakes ("when does shp opn?")
# ----------------------------------------------------------------------
def test_10_spelling_mistakes(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "when does shp opn?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is True
    assert "10 AM" in data["answer"]

# ----------------------------------------------------------------------
# 11. Greetings and gratitude
# ----------------------------------------------------------------------
def test_11_greetings_and_gratitude(client, shop_setup):
    # Greeting
    res1 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Hi"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res1.status_code == 200
    data1 = res1.get_json()["data"]
    assert data1["can_answer"] is True
    assert data1["status"] == "answered"
    assert "Hello" in data1["answer"] or "Welcome" in data1["answer"]

    # Gratitude
    res2 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Thanks a lot!"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res2.status_code == 200
    data2 = res2.get_json()["data"]
    assert data2["can_answer"] is True
    assert data2["status"] == "answered"
    assert "welcome" in data2["answer"].lower()

# ----------------------------------------------------------------------
# 12. Unknown information routes to Pending
# ----------------------------------------------------------------------
def test_12_unknown_information_routes_to_pending(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Do you sell rocket ships to Mars?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == "Thank you! The shop owner will reply to you soon by email."

# ----------------------------------------------------------------------
# 13. Damaged product complaint routes to Pending (Level 3 Escalation)
# ----------------------------------------------------------------------
def test_13_damaged_product_complaint_routes_to_pending(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "My phone was damaged when I received it."
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == "Thank you! The shop owner will reply to you soon by email."

# ----------------------------------------------------------------------
# 14. Payment issue routes to Pending (Level 3 Escalation)
# ----------------------------------------------------------------------
def test_14_payment_issue_routes_to_pending(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Payment failed but money was deducted from my account."
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == "Thank you! The shop owner will reply to you soon by email."

# ----------------------------------------------------------------------
# 15. Specific order tracking routes to Pending (Level 3 Escalation)
# ----------------------------------------------------------------------
def test_15_order_tracking_routes_to_pending(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Track my order #9876."
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == "Thank you! The shop owner will reply to you soon by email."

# ----------------------------------------------------------------------
# 16. Multi-tenant isolation
# ----------------------------------------------------------------------
def test_16_multitenant_knowledge_isolation(client, shop_setup):
    # Register Shop B (Sita Sarees)
    res_b = client.post("/api/auth/register", json={
        "full_name": "Sita Devi",
        "email": "sita@sitasarees.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Sita Sarees",
        "slug": "sita-sarees"
    })
    token_b = res_b.get_json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    client.post("/api/knowledge", json={
        "title": "Shop Timings",
        "content": "We open at 11:30 AM and close at 8 PM.",
        "category": "Timings"
    }, headers=headers_b)

    # Customer in Shop B
    sess_b = client.post("/api/public/shop/sita-sarees/session", json={
        "first_name": "Priya",
        "last_name": "Rao",
        "email": "priya@example.com"
    }).get_json()["data"]["session_token"]

    # Ask Shop B for opening time -> must return 11:30 AM, NOT Shop A's 10 AM
    res_b_chat = client.post("/api/public/shop/sita-sarees/chat", json={
        "message": "When does the shop open?"
    }, headers={"X-Customer-Session": sess_b})
    assert "11:30 AM" in res_b_chat.get_json()["data"]["answer"]
    assert "10 AM" not in res_b_chat.get_json()["data"]["answer"]

    # Ask Shop B for iPhone -> must NOT leak Shop A's iPhone knowledge
    res_b_phone = client.post("/api/public/shop/sita-sarees/chat", json={
        "message": "How much does the iPhone 15 cost?"
    }, headers={"X-Customer-Session": sess_b})
    assert res_b_phone.get_json()["data"]["can_answer"] is False
    assert res_b_phone.get_json()["data"]["status"] == "pending"

# ----------------------------------------------------------------------
# 17. Streaming response validation
# ----------------------------------------------------------------------
def test_17_streaming_response_validation(client, shop_setup):
    res = client.post("/api/public/shop/ravi-mobiles/chat/stream", json={
        "message": "When will the shop reopen?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    assert "text/event-stream" in res.content_type

    raw_data = res.get_data(as_text=True)
    assert "event: chunk" in raw_data
    assert "event: done" in raw_data
    assert "10 AM" in raw_data

# ----------------------------------------------------------------------
# 18. Pending record created for escalations
# ----------------------------------------------------------------------
def test_18_pending_record_created_for_escalations(client, shop_setup, app):
    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "I received a defective screen on my phone."
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    assert res.status_code == 200
    q_id = res.get_json()["data"]["question_id"]

    with app.app_context():
        q_record = db.session.get(CustomerQuestion, q_id)
        assert q_record is not None
        assert q_record.status == "pending"
        assert q_record.email_status == "pending"
        assert q_record.shop_id == shop_setup["shop_a_id"]

# ----------------------------------------------------------------------
# 19. Owner email notification triggered for pending
# ----------------------------------------------------------------------
def test_19_owner_email_notification_triggered_for_pending(client, shop_setup, app, monkeypatch):
    # Mock EmailService.send_customer_answer_email to verify notification trigger
    email_sent = False
    def mock_send(*args, **kwargs):
        nonlocal email_sent
        email_sent = True
        return {"success": True, "status": "sent", "error": None, "provider": "mock"}

    from backend.app.services.email_service import EmailService
    monkeypatch.setattr(EmailService, "send_customer_answer_email", mock_send)

    res = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Do you repair broken camera lenses?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    q_id = res.get_json()["data"]["question_id"]

    # Owner answers the pending question
    ans_res = client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Yes, we repair camera lenses within 2 business days."
    }, headers=shop_setup["headers_a"])
    assert ans_res.status_code == 200
    assert email_sent is True

    with app.app_context():
        q = db.session.get(CustomerQuestion, q_id)
        assert q.status == "answered"
        assert q.email_status == "sent"

# ----------------------------------------------------------------------
# 20. Automatic knowledge-base learning after owner answers
# ----------------------------------------------------------------------
def test_20_automatic_knowledge_learning_after_owner_answers(client, shop_setup, app, monkeypatch):
    from backend.app.services.email_service import EmailService
    monkeypatch.setattr(EmailService, "send_customer_answer_email", lambda *a, **k: {"success": True, "status": "sent", "error": None, "provider": "mock"})

    # 1. Ask unknown question -> goes to pending
    chat1 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Do you have student discounts?"
    }, headers={"X-Customer-Session": shop_setup["cust_token"]})
    q_id = chat1.get_json()["data"]["question_id"]
    assert chat1.get_json()["data"]["status"] == "pending"

    # 2. Owner answers pending question
    client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Yes, college students get a 5% discount on all accessories with valid student ID."
    }, headers=shop_setup["headers_a"])

    # 3. Knowledge base entry was created automatically
    with app.app_context():
        new_kb = KnowledgeBase.query.filter_by(
            shop_id=shop_setup["shop_a_id"],
            source_type="pending_answered"
        ).first()
        assert new_kb is not None
        assert "5% discount" in new_kb.content

    # 4. Another customer asks about student discounts -> AI answers immediately from learned knowledge!
    sess_res2 = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "Bina",
        "last_name": "Das",
        "email": "bina@example.com"
    })
    cust_token2 = sess_res2.get_json()["data"]["session_token"]

    chat2 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "Do you have student discounts?"
    }, headers={"X-Customer-Session": cust_token2})
    assert chat2.status_code == 200
    data2 = chat2.get_json()["data"]
    assert data2["can_answer"] is True
    assert data2["status"] == "answered"
    assert "5% discount" in data2["answer"]

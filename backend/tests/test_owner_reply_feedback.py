import pytest
from datetime import datetime, timezone
from backend.app.models import (
    db, Shop, User, Customer, CustomerSession, Conversation, Message, CustomerQuestion, AnswerFeedback
)
from backend.app.utils.security import hash_password, generate_session_token, hash_session_token

@pytest.fixture
def setup_owner_feedback_env(app):
    with app.app_context():
        # Shop A
        user_a = User(full_name="Owner A", email="owner.a@example.com", password_hash=hash_password("password123"))
        db.session.add(user_a)
        db.session.flush()

        shop_a = Shop(owner_id=user_a.id, shop_name="Alpha Electronics", slug="alpha-electronics")
        db.session.add(shop_a)
        db.session.flush()

        # Shop B
        user_b = User(full_name="Owner B", email="owner.b@example.com", password_hash=hash_password("password123"))
        db.session.add(user_b)
        db.session.flush()

        shop_b = Shop(owner_id=user_b.id, shop_name="Beta Fashion", slug="beta-fashion")
        db.session.add(shop_b)
        db.session.flush()

        # Customer 1 for Shop A
        cust_a1 = Customer(shop_id=shop_a.id, first_name="Alice", last_name="Customer", email="alice@example.com")
        db.session.add(cust_a1)
        db.session.flush()

        token_a1_raw = generate_session_token()
        session_a1 = CustomerSession(
            shop_id=shop_a.id,
            customer_id=cust_a1.id,
            session_token_hash=hash_session_token(token_a1_raw),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        db.session.add(session_a1)
        db.session.flush()

        conv_a1 = Conversation(shop_id=shop_a.id, customer_id=cust_a1.id, session_id=session_a1.id)
        db.session.add(conv_a1)
        db.session.flush()

        # Messages in conv_a1
        msg_cust = Message(shop_id=shop_a.id, conversation_id=conv_a1.id, sender_type="customer", message_content="Do you have gaming laptops?")
        db.session.add(msg_cust)
        db.session.flush()

        msg_ai_pending = Message(
            shop_id=shop_a.id,
            conversation_id=conv_a1.id,
            sender_type="ai",
            message_content="Thank you! The shop owner will reply to you soon by email."
        )
        db.session.add(msg_ai_pending)
        db.session.flush()

        q_a1 = CustomerQuestion(
            shop_id=shop_a.id,
            customer_id=cust_a1.id,
            conversation_id=conv_a1.id,
            question="Do you have gaming laptops?",
            ai_answer="Yes, we carry ASUS ROG and Razer laptops with 1 year warranty.",
            status="answered"
        )
        db.session.add(q_a1)
        db.session.flush()

        msg_owner = Message(
            shop_id=shop_a.id,
            conversation_id=conv_a1.id,
            sender_type="owner",
            message_content="Yes, we have ASUS ROG Strix in stock ready for pickup."
        )
        db.session.add(msg_owner)
        db.session.flush()

        # Customer 2 for Shop A (Different Customer, same shop)
        cust_a2 = Customer(shop_id=shop_a.id, first_name="Bob", last_name="Shopper", email="bob@example.com")
        db.session.add(cust_a2)
        db.session.flush()

        token_a2_raw = generate_session_token()
        session_a2 = CustomerSession(
            shop_id=shop_a.id,
            customer_id=cust_a2.id,
            session_token_hash=hash_session_token(token_a2_raw),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        db.session.add(session_a2)
        db.session.flush()

        conv_a2 = Conversation(shop_id=shop_a.id, customer_id=cust_a2.id, session_id=session_a2.id)
        db.session.add(conv_a2)
        db.session.flush()

        # Customer for Shop B
        cust_b = Customer(shop_id=shop_b.id, first_name="Charlie", last_name="Customer", email="charlie@example.com")
        db.session.add(cust_b)
        db.session.flush()

        token_b_raw = generate_session_token()
        session_b = CustomerSession(
            shop_id=shop_b.id,
            customer_id=cust_b.id,
            session_token_hash=hash_session_token(token_b_raw),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        db.session.add(session_b)
        db.session.flush()

        conv_b = Conversation(shop_id=shop_b.id, customer_id=cust_b.id, session_id=session_b.id)
        db.session.add(conv_b)
        db.session.flush()

        msg_owner_b = Message(
            shop_id=shop_b.id,
            conversation_id=conv_b.id,
            sender_type="owner",
            message_content="We have summer dresses on 20% discount."
        )
        db.session.add(msg_owner_b)
        db.session.flush()

        db.session.commit()

        return {
            "shop_a_id": shop_a.id,
            "shop_b_id": shop_b.id,
            "shop_a_slug": shop_a.slug,
            "shop_b_slug": shop_b.slug,
            "token_a1": token_a1_raw,
            "token_a2": token_a2_raw,
            "token_b": token_b_raw,
            "msg_owner_a_id": msg_owner.id,
            "msg_ai_pending_id": msg_ai_pending.id,
            "msg_cust_id": msg_cust.id,
            "q_a1_id": q_a1.id,
            "msg_owner_b_id": msg_owner_b.id
        }

def get_auth_token(client, email, password="password123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()["data"]["token"]


# -----------------------------------------------------------------------------
# 1. Accepts Good Feedback on Owner Reply
# -----------------------------------------------------------------------------
def test_01_accept_good_feedback_on_owner_reply(client, setup_owner_feedback_env, app):
    env = setup_owner_feedback_env
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["feedback_type"] == "good"
    assert data["data"]["target_type"] == "owner_reply"
    assert data["data"]["message_id"] == env["msg_owner_a_id"]

    with app.app_context():
        fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            message_id=env["msg_owner_a_id"],
            target_type="owner_reply"
        ).first()
        assert fb is not None
        assert fb.feedback_type == "good"


# -----------------------------------------------------------------------------
# 2. Accepts Bad Feedback on Owner Reply
# -----------------------------------------------------------------------------
def test_02_accept_bad_feedback_on_owner_reply(client, setup_owner_feedback_env, app):
    env = setup_owner_feedback_env
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "bad"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["feedback_type"] == "bad"
    assert data["data"]["target_type"] == "owner_reply"


# -----------------------------------------------------------------------------
# 3. Rejects Invalid Feedback Values
# -----------------------------------------------------------------------------
def test_03_rejects_invalid_feedback_values(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    for invalid_val in ["neutral", "average", "terrible", "excellent", ""]:
        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
            headers={"X-Customer-Session": env["token_a1"]},
            json={"message_id": env["msg_owner_a_id"], "feedback_type": invalid_val}
        )
        assert res.status_code == 400
        assert "feedback_type must be either 'good' or 'bad'" in res.get_json()["message"]


# -----------------------------------------------------------------------------
# 4. Requires Customer Session Authentication
# -----------------------------------------------------------------------------
def test_04_requires_customer_session_authentication(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # No header or body token
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res.status_code == 401

    # Fake / invalid token
    res_fake = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": "invalid_session_token_xyz"},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res_fake.status_code == 401


# -----------------------------------------------------------------------------
# 5. Prevents Cross-Tenant Feedback Submission
# -----------------------------------------------------------------------------
def test_05_prevents_cross_tenant_feedback_submission(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Customer from Shop B attempts to rate Shop A's owner reply
    res = client.post(
        f"/api/public/shop/{env['shop_b_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_b"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res.status_code == 404
    assert "Message not found or unauthorized for this shop" in res.get_json()["message"]


# -----------------------------------------------------------------------------
# 6. Prevents Rating Non-Owner Messages
# -----------------------------------------------------------------------------
def test_06_prevents_rating_non_owner_messages(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Attempt to submit owner-reply feedback on AI pending fallback message
    res_ai = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_ai_pending_id"], "feedback_type": "good"}
    )
    assert res_ai.status_code == 400
    assert "Feedback can only be submitted for shop owner replies" in res_ai.get_json()["message"]

    # Attempt to submit owner-reply feedback on customer message
    res_cust = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_cust_id"], "feedback_type": "good"}
    )
    assert res_cust.status_code == 400
    assert "Feedback can only be submitted for shop owner replies" in res_cust.get_json()["message"]


# -----------------------------------------------------------------------------
# 7. Prevents Customer from Rating Another Customer's Owner Reply
# -----------------------------------------------------------------------------
def test_07_prevents_rating_another_customers_owner_reply(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Customer A2 belongs to Shop A, but does NOT own conv_a1
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a2"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res.status_code == 403
    assert "You are not authorized to rate this message" in res.get_json()["message"]


# -----------------------------------------------------------------------------
# 8. One-Time Feedback Enforcement (Rejects Second Submission with HTTP 409 Conflict)
# -----------------------------------------------------------------------------
def test_08_one_time_feedback_rejects_second_submission_with_409(client, setup_owner_feedback_env, app):
    env = setup_owner_feedback_env
    # 1. First submission (Good) succeeds
    res1 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )
    assert res1.status_code == 200
    assert res1.get_json()["data"]["feedback_type"] == "good"

    # 2. Second submission on the same owner reply MUST be rejected with HTTP 409 Conflict
    res2 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "bad"}
    )
    assert res2.status_code == 409
    assert "already been submitted" in res2.get_json()["message"]

    # 3. Database record must be unchanged and NOT duplicated
    with app.app_context():
        feedbacks = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            message_id=env["msg_owner_a_id"],
            target_type="owner_reply"
        ).all()
        assert len(feedbacks) == 1
        assert feedbacks[0].feedback_type == "good"


# -----------------------------------------------------------------------------
# 9. Owner Reply Feedback Does NOT Overwrite AI Answer Feedback
# -----------------------------------------------------------------------------
def test_09_owner_reply_feedback_does_not_overwrite_ai_answer_feedback(client, setup_owner_feedback_env, app):
    env = setup_owner_feedback_env
    # 1. Customer submits AI answer feedback (thumbs up / good)
    res_ai_fb = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"question_id": env["q_a1_id"], "feedback_type": "good"}
    )
    assert res_ai_fb.status_code == 200

    # 2. Customer submits Owner reply feedback (thumbs down / bad)
    res_owner_fb = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "bad"}
    )
    assert res_owner_fb.status_code == 200

    # 3. Verify in database: AI feedback is PRESERVED, owner feedback is SEPARATE
    with app.app_context():
        ai_fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            customer_question_id=env["q_a1_id"],
            target_type="ai_answer"
        ).first()
        assert ai_fb is not None
        assert ai_fb.feedback_type == "good"

        owner_fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            message_id=env["msg_owner_a_id"],
            target_type="owner_reply"
        ).first()
        assert owner_fb is not None
        assert owner_fb.feedback_type == "bad"


# -----------------------------------------------------------------------------
# 10. Dashboard Displays Correct Owner Reply Metrics
# -----------------------------------------------------------------------------
def test_10_dashboard_displays_owner_reply_metrics(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Submit owner feedback
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )

    auth_token = get_auth_token(client, "owner.a@example.com")
    res = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    stats = res.get_json()["data"]["stats"]

    assert stats["good_owner_replies"] == 1
    assert stats["bad_owner_replies"] == 0
    assert stats["total_owner_replies_rated"] == 1
    assert stats["owner_helpfulness_percentage"] == 100.0


# -----------------------------------------------------------------------------
# 11. Owner Replies Listing Endpoint and Search/Filters
# -----------------------------------------------------------------------------
def test_11_owner_replies_listing_and_filters(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Submit owner feedback
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )

    auth_token = get_auth_token(client, "owner.a@example.com")
    # All items
    res = client.get("/api/feedback/owner-replies", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total"] == 1
    assert data["total_good"] == 1
    assert data["total_bad"] == 0
    assert data["helpfulness_percentage"] == 100.0
    assert data["items"][0]["feedback_type"] == "good"
    assert data["items"][0]["customer_email"] == "alice@example.com"

    # Filter by type=bad (should return 0)
    res_bad = client.get("/api/feedback/owner-replies?type=bad", headers={"Authorization": f"Bearer {auth_token}"})
    assert res_bad.get_json()["data"]["total"] == 0

    # Search filter
    res_search = client.get("/api/feedback/owner-replies?q=ASUS", headers={"Authorization": f"Bearer {auth_token}"})
    assert res_search.get_json()["data"]["total"] == 1


# -----------------------------------------------------------------------------
# 12. Multi-Tenant Isolation Across Shops
# -----------------------------------------------------------------------------
def test_12_multitenant_isolation(client, setup_owner_feedback_env):
    env = setup_owner_feedback_env
    # Submit feedback for Shop A
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a1"]},
        json={"message_id": env["msg_owner_a_id"], "feedback_type": "good"}
    )

    # Login as Shop B owner
    auth_token_b = get_auth_token(client, "owner.b@example.com")
    res_b = client.get("/api/feedback/owner-replies", headers={"Authorization": f"Bearer {auth_token_b}"})
    assert res_b.status_code == 200
    assert res_b.get_json()["data"]["total"] == 0
    assert res_b.get_json()["data"]["total_good"] == 0

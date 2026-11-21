import pytest
from datetime import datetime, timezone
from backend.app.models import (
    db, Shop, User, Customer, CustomerSession, Conversation, Message, CustomerQuestion, AnswerFeedback
)
from backend.app.utils.security import hash_password, generate_session_token, hash_session_token

@pytest.fixture
def setup_feedback_test_env(app):
    with app.app_context():
        # Shop A
        user_a = User(full_name="Owner A", email="owner.a@example.com", password_hash=hash_password("password123"))
        db.session.add(user_a)
        db.session.flush()

        shop_a = Shop(owner_id=user_a.id, shop_name="Alpha Store", slug="alpha-store")
        db.session.add(shop_a)
        db.session.flush()

        # Shop B
        user_b = User(full_name="Owner B", email="owner.b@example.com", password_hash=hash_password("password123"))
        db.session.add(user_b)
        db.session.flush()

        shop_b = Shop(owner_id=user_b.id, shop_name="Beta Store", slug="beta-store")
        db.session.add(shop_b)
        db.session.flush()

        # Customer for Shop A
        cust_a = Customer(shop_id=shop_a.id, first_name="Alice", last_name="Alpha", email="alice@example.com")
        db.session.add(cust_a)
        db.session.flush()

        token_a_raw = generate_session_token()
        session_a = CustomerSession(
            shop_id=shop_a.id,
            customer_id=cust_a.id,
            session_token_hash=hash_session_token(token_a_raw),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        db.session.add(session_a)
        db.session.flush()

        conv_a = Conversation(shop_id=shop_a.id, customer_id=cust_a.id, session_id=session_a.id)
        db.session.add(conv_a)
        db.session.flush()

        # Answered AI Question for Shop A
        q_ai_answered = CustomerQuestion(
            shop_id=shop_a.id,
            customer_id=cust_a.id,
            conversation_id=conv_a.id,
            question="What are your opening hours?",
            ai_answer="We are open Monday to Friday from 9 AM to 7 PM.",
            status="answered"
        )
        db.session.add(q_ai_answered)
        db.session.flush()

        msg_ai = Message(
            shop_id=shop_a.id,
            conversation_id=conv_a.id,
            sender_type="ai",
            message_content="We are open Monday to Friday from 9 AM to 7 PM."
        )
        db.session.add(msg_ai)
        db.session.flush()

        # Pending Question for Shop A (unanswered)
        q_pending = CustomerQuestion(
            shop_id=shop_a.id,
            customer_id=cust_a.id,
            conversation_id=conv_a.id,
            question="Do you sell custom mechanical keyboards?",
            ai_answer=None,
            status="pending"
        )
        db.session.add(q_pending)
        db.session.flush()

        msg_pending = Message(
            shop_id=shop_a.id,
            conversation_id=conv_a.id,
            sender_type="ai",
            message_content="Thank you! The shop owner will reply to you soon by email."
        )
        db.session.add(msg_pending)
        db.session.flush()

        # Owner Reply for Shop A
        msg_owner = Message(
            shop_id=shop_a.id,
            conversation_id=conv_a.id,
            sender_type="owner",
            message_content="Yes, we offer custom solder and hot-swap mechanical keyboards."
        )
        db.session.add(msg_owner)
        db.session.flush()

        # Customer for Shop B
        cust_b = Customer(shop_id=shop_b.id, first_name="Bob", last_name="Beta", email="bob@example.com")
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

        q_b = CustomerQuestion(
            shop_id=shop_b.id,
            customer_id=cust_b.id,
            conversation_id=conv_b.id,
            question="Do you have silk shirts?",
            ai_answer="Yes, 100% pure silk shirts in stock.",
            status="answered"
        )
        db.session.add(q_b)
        db.session.flush()

        db.session.commit()

        return {
            "shop_a_id": shop_a.id,
            "shop_b_id": shop_b.id,
            "shop_a_slug": shop_a.slug,
            "shop_b_slug": shop_b.slug,
            "token_a": token_a_raw,
            "token_b": token_b_raw,
            "q_ai_answered_id": q_ai_answered.id,
            "q_pending_id": q_pending.id,
            "msg_owner_id": msg_owner.id,
            "q_b_id": q_b.id
        }

def get_auth_token(client, email, password="password123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()["data"]["token"]


# -----------------------------------------------------------------------------
# 1. Good Feedback Submission
# -----------------------------------------------------------------------------
def test_01_good_feedback_submission(client, setup_feedback_test_env, app):
    env = setup_feedback_test_env
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["feedback_type"] == "good"

    with app.app_context():
        fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            customer_question_id=env["q_ai_answered_id"],
            target_type="ai_answer"
        ).first()
        assert fb is not None
        assert fb.feedback_type == "good"


# -----------------------------------------------------------------------------
# 2. Bad Feedback Submission
# -----------------------------------------------------------------------------
def test_02_bad_feedback_submission(client, setup_feedback_test_env, app):
    env = setup_feedback_test_env
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "bad", "comment": "Incorrect opening hours"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["feedback_type"] == "bad"

    with app.app_context():
        fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            customer_question_id=env["q_ai_answered_id"],
            target_type="ai_answer"
        ).first()
        assert fb is not None
        assert fb.feedback_type == "bad"
        assert fb.reason == "Incorrect opening hours"


# -----------------------------------------------------------------------------
# 3. Good-to-Bad Update
# -----------------------------------------------------------------------------
def test_03_good_to_bad_update(client, setup_feedback_test_env, app):
    env = setup_feedback_test_env
    # 1. Submit Good
    res1 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    assert res1.status_code == 200

    # 2. Update to Bad
    res2 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "bad"}
    )
    assert res2.status_code == 200
    assert res2.get_json()["data"]["feedback_type"] == "bad"

    # Confirm only 1 database record exists (no duplicate)
    with app.app_context():
        fbs = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            customer_question_id=env["q_ai_answered_id"],
            target_type="ai_answer"
        ).all()
        assert len(fbs) == 1
        assert fbs[0].feedback_type == "bad"


# -----------------------------------------------------------------------------
# 4. Bad-to-Good Update
# -----------------------------------------------------------------------------
def test_04_bad_to_good_update(client, setup_feedback_test_env, app):
    env = setup_feedback_test_env
    # 1. Submit Bad
    res1 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "bad"}
    )
    assert res1.status_code == 200

    # 2. Update to Good
    res2 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    assert res2.status_code == 200
    assert res2.get_json()["data"]["feedback_type"] == "good"

    with app.app_context():
        fbs = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            customer_question_id=env["q_ai_answered_id"],
            target_type="ai_answer"
        ).all()
        assert len(fbs) == 1
        assert fbs[0].feedback_type == "good"


# -----------------------------------------------------------------------------
# 5. Dashboard Counts and Percentage Calculations
# -----------------------------------------------------------------------------
def test_05_dashboard_counts_and_percentage_calculations(client, setup_feedback_test_env):
    env = setup_feedback_test_env
    # Submit AI Good
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    # Submit Owner Good
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message_id": env["msg_owner_id"], "feedback_type": "good"}
    )

    auth_token = get_auth_token(client, "owner.a@example.com")
    res = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    stats = res.get_json()["data"]["stats"]

    assert stats["good_owner_replies"] == 1
    assert stats["bad_owner_replies"] == 0
    assert stats["total_owner_replies_rated"] == 1
    assert stats["owner_helpfulness_percentage"] == 100.0
    assert stats["total_good"] == 1
    assert stats["total_bad"] == 0
    assert stats["total_rated"] == 1
    assert stats["helpfulness_percentage"] == 100.0

    # Ensure star ratings are completely absent
    assert "average_rating" not in stats
    assert "total_ratings" not in stats
    assert "rating_distribution" not in stats


# -----------------------------------------------------------------------------
# 6. Owner Reply Feedback and AI Feedback Remain Separate
# -----------------------------------------------------------------------------
def test_06_owner_reply_and_ai_feedback_remain_separate(client, setup_feedback_test_env, app):
    env = setup_feedback_test_env
    # 1. Rate AI Answer as Good
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )

    # 2. Rate Owner Reply as Bad
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message_id": env["msg_owner_id"], "feedback_type": "bad"}
    )

    with app.app_context():
        ai_fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            target_type="ai_answer"
        ).first()
        owner_fb = AnswerFeedback.query.filter_by(
            shop_id=env["shop_a_id"],
            target_type="owner_reply"
        ).first()

        assert ai_fb is not None
        assert ai_fb.feedback_type == "good"

        assert owner_fb is not None
        assert owner_fb.feedback_type == "bad"


# -----------------------------------------------------------------------------
# 7. Feedback Persistence After Page Refresh / Session Validate
# -----------------------------------------------------------------------------
def test_07_feedback_persistence_after_page_refresh(client, setup_feedback_test_env):
    env = setup_feedback_test_env
    # Submit AI Good
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    # Submit Owner Bad
    client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message_id": env["msg_owner_id"], "feedback_type": "bad"}
    )

    # Call validate_session endpoint
    res = client.get(
        f"/api/public/shop/{env['shop_a_slug']}/session/validate",
        headers={"X-Customer-Session": env["token_a"]}
    )
    assert res.status_code == 200
    msgs = res.get_json()["data"]["messages"]

    ai_msg = next((m for m in msgs if m["sender_type"] == "ai" and m.get("question_id") == env["q_ai_answered_id"]), None)
    owner_msg = next((m for m in msgs if m["sender_type"] == "owner" and m["id"] == env["msg_owner_id"]), None)

    assert ai_msg is not None
    assert ai_msg["feedback"]["feedback_type"] == "good"

    assert owner_msg is not None
    assert owner_msg["feedback_type"] == "bad"


# -----------------------------------------------------------------------------
# 8. Pending Messages Cannot Be Rated
# -----------------------------------------------------------------------------
def test_08_pending_messages_cannot_be_rated(client, setup_feedback_test_env):
    env = setup_feedback_test_env
    # Attempt to rate unanswered pending question
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"question_id": env["q_pending_id"], "feedback_type": "good"}
    )
    assert res.status_code == 400
    assert "Only eligible AI-generated answers can be rated" in res.get_json()["message"]


# -----------------------------------------------------------------------------
# 9. Multi-Tenant Isolation
# -----------------------------------------------------------------------------
def test_09_multitenant_isolation(client, setup_feedback_test_env):
    env = setup_feedback_test_env
    # Customer B attempts to rate Shop A's AI answer
    res = client.post(
        f"/api/public/shop/{env['shop_b_slug']}/feedback",
        headers={"X-Customer-Session": env["token_b"]},
        json={"question_id": env["q_ai_answered_id"], "feedback_type": "good"}
    )
    assert res.status_code == 404
    assert "Question not found or unauthorized for this shop" in res.get_json()["message"]


# -----------------------------------------------------------------------------
# 10. Rejects Invalid Feedback Values
# -----------------------------------------------------------------------------
def test_10_rejects_invalid_feedback_values(client, setup_feedback_test_env):
    env = setup_feedback_test_env
    for val in ["5", "stars", "great", 4, None]:
        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/feedback",
            headers={"X-Customer-Session": env["token_a"]},
            json={"question_id": env["q_ai_answered_id"], "feedback_type": val}
        )
        assert res.status_code == 400
        assert "feedback_type must be either 'good' or 'bad'" in res.get_json()["message"]

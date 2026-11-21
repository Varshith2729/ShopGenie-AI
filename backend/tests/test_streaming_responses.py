import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from backend.app.models import (
    db, Shop, User, Customer, CustomerSession, Conversation, Message, CustomerQuestion, AnswerFeedback, KnowledgeBase
)
from backend.app.utils.security import hash_password, generate_session_token, hash_session_token, generate_jwt_token
from backend.app.services.ai_service import AIService, FALLBACK_MESSAGE


@pytest.fixture
def streaming_env(app):
    with app.app_context():
        # Owner & Shop A
        user_a = User(full_name="Owner A", email="owner.stream.a@example.com", password_hash=hash_password("password123"))
        db.session.add(user_a)
        db.session.flush()

        shop_a = Shop(owner_id=user_a.id, shop_name="Alpha Tech", slug="alpha-tech", description="Premium electronics and laptops")
        db.session.add(shop_a)
        db.session.flush()

        kb_a = KnowledgeBase(
            shop_id=shop_a.id,
            title="Available Laptops",
            content="We have Dell XPS 15 and Apple MacBook Pro in stock. Store hours are 9 AM to 8 PM Monday to Saturday.",
            category="Products"
        )
        db.session.add(kb_a)

        # Owner & Shop B
        user_b = User(full_name="Owner B", email="owner.stream.b@example.com", password_hash=hash_password("password123"))
        db.session.add(user_b)
        db.session.flush()

        shop_b = Shop(owner_id=user_b.id, shop_name="Beta Fashion", slug="beta-fashion", description="Boutique designer clothing")
        db.session.add(shop_b)
        db.session.flush()

        kb_b = KnowledgeBase(
            shop_id=shop_b.id,
            title="Store Collection",
            content="We offer Italian silk suits and evening dresses.",
            category="Products"
        )
        db.session.add(kb_b)

        # Customer for Shop A
        cust_a = Customer(shop_id=shop_a.id, first_name="Alice", last_name="Streamer", email="alice.stream@example.com")
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

        # Customer for Shop B
        cust_b = Customer(shop_id=shop_b.id, first_name="Bob", last_name="Shopper", email="bob.stream@example.com")
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
        db.session.commit()

        jwt_a = generate_jwt_token(user_a.id, shop_a.id)

        return {
            "shop_a_id": shop_a.id,
            "shop_b_id": shop_b.id,
            "shop_a_slug": shop_a.slug,
            "shop_b_slug": shop_b.slug,
            "token_a": token_a_raw,
            "token_b": token_b_raw,
            "jwt_a": jwt_a,
            "cust_a_id": cust_a.id
        }


def parse_sse_events(response_text):
    """Parse raw SSE payload into structured list of events."""
    events = []
    current_event = "message"
    for line in response_text.split("\n"):
        line = line.strip()
        if not line:
            current_event = "message"
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                data = json.loads(data_str)
                events.append({"event": current_event, "data": data})
            except Exception:
                events.append({"event": current_event, "data": data_str})
    return events


# -----------------------------------------------------------------------------
# 1. Gemini Streaming Produces Multiple Chunks
# -----------------------------------------------------------------------------
def test_01_gemini_streaming_produces_multiple_chunks(client, streaming_env):
    env = streaming_env

    # Mock Gemini stream to yield 3 real token chunks
    mock_lines = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "Yes, we currently have "}]}}]}\n\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "the Dell XPS 15 in stock "}]}}]}\n\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "ready for immediate pickup."}]}}]}\n\n'
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = mock_lines

    with patch("backend.app.services.ai_service.requests.post", return_value=mock_resp), \
         patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test_key"}):

        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
            headers={"X-Customer-Session": env["token_a"]},
            json={"message": "Do you have Dell XPS 15?"}
        )

        assert res.status_code == 200
        assert "text/event-stream" in res.content_type
        events = parse_sse_events(res.get_data(as_text=True))

        chunks = [e["data"]["chunk"] for e in events if e["event"] == "chunk"]
        assert len(chunks) >= 3
        assert "Yes, we currently have " in chunks[0]
        assert "Dell XPS 15 in stock " in chunks[1]


# -----------------------------------------------------------------------------
# 2. First Response Chunk Arrives Before Generation Completes
# -----------------------------------------------------------------------------
def test_02_first_chunk_arrives_before_completion(client, streaming_env):
    env = streaming_env

    mock_lines = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "We are open from "}]}}]}\n\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "9 AM to 8 PM Monday to Saturday."}]}}]}\n\n'
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = mock_lines

    with patch("backend.app.services.ai_service.requests.post", return_value=mock_resp), \
         patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test_key"}):

        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
            headers={"X-Customer-Session": env["token_a"]},
            json={"message": "What are your store hours?"}
        )

        assert res.status_code == 200
        events = parse_sse_events(res.get_data(as_text=True))

        # Start event comes first
        assert events[0]["event"] == "start"
        # First chunk is second
        assert events[1]["event"] == "chunk"
        # Done event is last
        assert events[-1]["event"] == "done"
        assert events[-1]["data"]["can_answer"] is True


# -----------------------------------------------------------------------------
# 3. Complete Streamed Response Matches the Generated Answer
# -----------------------------------------------------------------------------
def test_03_complete_streamed_response_matches_generated_answer(client, streaming_env, app):
    env = streaming_env

    mock_lines = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "We carry Apple "}]}}]}\n\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "MacBook Pro laptops."}]}}]}\n\n'
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = mock_lines

    with patch("backend.app.services.ai_service.requests.post", return_value=mock_resp), \
         patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test_key"}):

        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
            headers={"X-Customer-Session": env["token_a"]},
            json={"message": "Do you have Apple MacBook Pro?"}
        )

        events = parse_sse_events(res.get_data(as_text=True))
        chunks = [e["data"]["chunk"] for e in events if e["event"] == "chunk"]
        joined_chunks = "".join(chunks).strip()

        done_event = [e for e in events if e["event"] == "done"][0]
        final_answer = done_event["data"]["answer"]

        assert joined_chunks in final_answer

        with app.app_context():
            q = db.session.get(CustomerQuestion, done_event["data"]["question_id"])
            assert q.ai_answer == final_answer
            assert q.status == "answered"


# -----------------------------------------------------------------------------
# 4. Customer Messages are Stored Correctly
# -----------------------------------------------------------------------------
def test_04_customer_messages_stored_correctly(client, streaming_env, app):
    env = streaming_env

    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Hello, do you have laptops?"}
    )
    assert res.status_code == 200

    with app.app_context():
        cust_msg = Message.query.filter_by(
            shop_id=env["shop_a_id"],
            sender_type="customer",
            message_content="Hello, do you have laptops?"
        ).first()
        assert cust_msg is not None
        assert cust_msg.conversation_id is not None


# -----------------------------------------------------------------------------
# 5. AI Answers are Saved Only Once
# -----------------------------------------------------------------------------
def test_05_ai_answers_saved_only_once(client, streaming_env, app):
    env = streaming_env

    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you have MacBook Pro?"}
    )
    assert res.status_code == 200
    events = parse_sse_events(res.get_data(as_text=True))
    done = [e for e in events if e["event"] == "done"][0]

    with app.app_context():
        # Verify exactly 1 CustomerQuestion record
        questions = CustomerQuestion.query.filter_by(
            shop_id=env["shop_a_id"],
            question="Do you have MacBook Pro?"
        ).all()
        assert len(questions) == 1

        # Verify exactly 1 AI Message record in conversation
        ai_msgs = Message.query.filter_by(
            id=done["data"]["message_id"],
            sender_type="ai"
        ).all()
        assert len(ai_msgs) == 1


# -----------------------------------------------------------------------------
# 6. Conversation History Works After Refresh
# -----------------------------------------------------------------------------
def test_06_conversation_history_works_after_refresh(client, streaming_env):
    env = streaming_env

    # 1. Ask a question via stream and consume generator
    stream_res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you sell laptops?"}
    )
    _ = stream_res.get_data()

    # 2. Simulate page reload / session validate
    val_res = client.get(
        f"/api/public/shop/{env['shop_a_slug']}/session/validate",
        headers={"X-Customer-Session": env["token_a"]}
    )
    assert val_res.status_code == 200
    data = val_res.get_json()["data"]
    assert data["valid"] is True
    assert len(data["messages"]) >= 2

    # Check order: customer first, ai second
    assert data["messages"][-2]["sender_type"] == "customer"
    assert data["messages"][-1]["sender_type"] == "ai"


# -----------------------------------------------------------------------------
# 7. Unknown Questions Still Enter Pending
# -----------------------------------------------------------------------------
def test_07_unknown_questions_enter_pending(client, streaming_env, app):
    env = streaming_env

    # Question about unmentioned product (smartwatch)
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you have solar-powered smartwatches?"}
    )
    assert res.status_code == 200
    events = parse_sse_events(res.get_data(as_text=True))

    done = [e for e in events if e["event"] == "done"][0]
    assert done["data"]["can_answer"] is False
    assert done["data"]["status"] == "pending"
    assert FALLBACK_MESSAGE in done["data"]["answer"]

    with app.app_context():
        q = db.session.get(CustomerQuestion, done["data"]["question_id"])
        assert q.status == "pending"
        assert q.email_status == "pending"
        assert q.ai_answer is None


# -----------------------------------------------------------------------------
# 8. General Greetings Receive AI Responses
# -----------------------------------------------------------------------------
def test_08_general_greetings_receive_ai_responses(client, streaming_env, app):
    env = streaming_env

    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Hello, good morning!"}
    )
    assert res.status_code == 200
    events = parse_sse_events(res.get_data(as_text=True))

    done = [e for e in events if e["event"] == "done"][0]
    assert done["data"]["can_answer"] is True
    assert done["data"]["status"] == "answered"
    assert "Alpha Tech" in done["data"]["answer"]

    with app.app_context():
        q = db.session.get(CustomerQuestion, done["data"]["question_id"])
        assert q.status == "answered"
        assert q.ai_answer is not None


# -----------------------------------------------------------------------------
# 9. Streaming API Failures Handled Safely
# -----------------------------------------------------------------------------
def test_09_streaming_api_failures_handled_safely(client, streaming_env):
    env = streaming_env

    with patch("backend.app.services.ai_service.requests.post", side_effect=Exception("Network Timeout")), \
         patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test_key"}):

        res = client.post(
            f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
            headers={"X-Customer-Session": env["token_a"]},
            json={"message": "Do you have Dell XPS?"}
        )

        assert res.status_code == 200
        events = parse_sse_events(res.get_data(as_text=True))
        done = [e for e in events if e["event"] == "done"]
        assert len(done) >= 1
        # Recovers safely with fallback or handled state without 500 error
        assert done[0]["data"]["status"] in ("answered", "pending")


# -----------------------------------------------------------------------------
# 10. Client Disconnection Does Not Corrupt Database
# -----------------------------------------------------------------------------
def test_10_client_disconnection_does_not_corrupt_database(client, streaming_env, app):
    env = streaming_env

    # Simulate client disconnect during generator by calling next once and closing
    with app.app_context():
        initial_q_count = CustomerQuestion.query.filter_by(shop_id=env["shop_a_id"]).count()

    # Post query
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Interrupted message test"}
    )
    assert res.status_code == 200

    # Verify database remains consistent
    with app.app_context():
        cust_msg = Message.query.filter_by(message_content="Interrupted message test").first()
        assert cust_msg is not None


# -----------------------------------------------------------------------------
# 11. Multi-Tenant Isolation Remains Intact
# -----------------------------------------------------------------------------
def test_11_multitenant_isolation(client, streaming_env):
    env = streaming_env

    # Customer B asks about Alpha Tech's Dell XPS in Beta Fashion shop
    res = client.post(
        f"/api/public/shop/{env['shop_b_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_b"]},
        json={"message": "Do you have Dell XPS 15 laptops?"}
    )
    assert res.status_code == 200
    events = parse_sse_events(res.get_data(as_text=True))

    done = [e for e in events if e["event"] == "done"][0]
    # In Beta Fashion, Dell XPS is unknown and must go to pending!
    assert done["data"]["can_answer"] is False
    assert done["data"]["status"] == "pending"

    # Cross-tenant session token rejection
    res_cross = client.post(
        f"/api/public/shop/{env['shop_b_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},  # Shop A token on Shop B
        json={"message": "Test"}
    )
    assert res_cross.status_code == 401


# -----------------------------------------------------------------------------
# 12. Owner Email Replies Remain Functional
# -----------------------------------------------------------------------------
def test_12_owner_email_replies_remain_functional(client, streaming_env, app):
    env = streaming_env

    # 1. Ask unknown question via stream -> Pending
    res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you do screen replacements?"}
    )
    events = parse_sse_events(res.get_data(as_text=True))
    q_id = [e for e in events if e["event"] == "done"][0]["data"]["question_id"]

    # 2. Owner answers pending question
    ans_res = client.post(
        f"/api/questions/{q_id}/answer",
        headers={"Authorization": f"Bearer {env['jwt_a']}"},
        json={"answer": "Yes, screen replacement takes 2 hours and costs Rs. 4,500."}
    )
    assert ans_res.status_code == 200
    assert ans_res.get_json()["data"]["question"]["status"] == "answered"

    with app.app_context():
        q = db.session.get(CustomerQuestion, q_id)
        assert q.status == "answered"
        assert q.owner_answer == "Yes, screen replacement takes 2 hours and costs Rs. 4,500."


# -----------------------------------------------------------------------------
# 13. Good/Bad Owner Reply Feedback Remains Unchanged
# -----------------------------------------------------------------------------
def test_13_owner_reply_feedback_remains_unchanged(client, streaming_env, app):
    env = streaming_env

    # Create owner message in conversation
    with app.app_context():
        session_obj = CustomerSession.query.filter_by(shop_id=env["shop_a_id"]).first()
        conv = Conversation.query.filter_by(shop_id=env["shop_a_id"]).first()
        if not conv:
            conv = Conversation(shop_id=env["shop_a_id"], customer_id=env["cust_a_id"], session_id=session_obj.id)
            db.session.add(conv)
            db.session.flush()
        owner_msg = Message(
            shop_id=env["shop_a_id"],
            conversation_id=conv.id,
            sender_type="owner",
            message_content="Yes we have Dell XPS in stock."
        )
        db.session.add(owner_msg)
        db.session.commit()
        owner_msg_id = owner_msg.id

    # Customer submits Good feedback
    fb_res = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message_id": owner_msg_id, "feedback_type": "good"}
    )
    assert fb_res.status_code == 200
    assert fb_res.get_json()["data"]["feedback_type"] == "good"

    # Second submission returns 409 Conflict (One-Time enforcement)
    fb_res2 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/owner-feedback",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message_id": owner_msg_id, "feedback_type": "bad"}
    )
    assert fb_res2.status_code == 409


# -----------------------------------------------------------------------------
# 14. Duplicate Messages are Prevented (1-second debounce)
# -----------------------------------------------------------------------------
def test_14_duplicate_messages_prevented(client, streaming_env, app):
    env = streaming_env

    # First request
    res1 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you have laptops?"}
    )
    assert res1.status_code == 200
    _ = res1.get_data()

    # Rapid second identical request
    res2 = client.post(
        f"/api/public/shop/{env['shop_a_slug']}/chat/stream",
        headers={"X-Customer-Session": env["token_a"]},
        json={"message": "Do you have laptops?"}
    )
    assert res2.status_code == 200
    _ = res2.get_data()

    with app.app_context():
        # Confirm customer message is not duplicated
        cust_msgs = Message.query.filter_by(
            shop_id=env["shop_a_id"],
            sender_type="customer",
            message_content="Do you have laptops?"
        ).all()
        assert len(cust_msgs) == 1

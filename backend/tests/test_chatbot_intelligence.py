import pytest
from unittest.mock import patch
import requests
from backend.app.models import db, Shop, User, KnowledgeBase, Customer, CustomerSession, Conversation, Message, CustomerQuestion, AnswerFeedback
from backend.app.services.search_service import search_shop_knowledge
from backend.app.services.ai_service import AIService, FALLBACK_MESSAGE, sanitize_customer_answer

def _setup_shop_and_session(client, slug, email, shop_name):
    """Helper to create a shop, knowledge entries, and a customer session."""
    user = User(email=f"owner_{slug}@test.com", full_name="Shop Owner", password_hash="dummy_hash")
    db.session.add(user)
    db.session.flush()

    shop = Shop(owner_id=user.id, shop_name=shop_name, slug=slug)
    db.session.add(shop)
    db.session.flush()

    # Add standard knowledge base entries
    k1 = KnowledgeBase(
        shop_id=shop.id,
        category="Timings",
        title="Store Timings",
        content="Our shop opens at 9:00 AM and closes at 9:00 PM Monday through Saturday. We are closed on Sunday."
    )
    k2 = KnowledgeBase(
        shop_id=shop.id,
        category="Products",
        title="Products and Brands",
        content="We sell Samsung, Apple, Vivo, Oppo, and OnePlus smartphones and official accessories."
    )
    k3 = KnowledgeBase(
        shop_id=shop.id,
        category="Policy",
        title="Return Policy",
        content="Customers can return unused products within 7 days. Original bills and intact packaging are mandatory."
    )
    db.session.add_all([k1, k2, k3])
    db.session.commit()

    # Establish customer session
    res = client.post(f"/api/public/shop/{slug}/session", json={
        "first_name": "Alice",
        "last_name": "Smith",
        "email": email
    })
    assert res.status_code == 201
    token = res.get_json()["data"]["session_token"]
    return shop, token

# 1. Normal AI answer
def test_01_normal_ai_answer(client):
    shop, token = _setup_shop_and_session(client, "normal-shop-1", "alice1@test.com", "Alpha Tech")
    headers = {"X-Customer-Session": token}

    res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "What time do you open?"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert data["answer"]
    assert "9:00 AM" in data["answer"] or "9" in data["answer"]
    assert data["question_id"] is not None

    q = db.session.get(CustomerQuestion, data["question_id"])
    assert q is not None
    assert q.status == "answered"
    assert q.ai_answer == data["answer"]

# 2. Empty AI response
def test_02_empty_ai_response(client):
    shop, token = _setup_shop_and_session(client, "empty-shop-2", "alice2@test.com", "Beta Tech")
    headers = {"X-Customer-Session": token}

    with patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
        with patch.object(AIService, "_call_gemini", return_value={"can_answer": True, "answer": "", "provider": "gemini"}):
            res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
                "message": "Tell me about your phones"
            })
            assert res.status_code == 200
            data = res.get_json()["data"]

            # Must NOT return empty string to customer
            assert data["answer"] == FALLBACK_MESSAGE
            assert data["can_answer"] is False
            assert data["status"] == "pending"

            q = db.session.get(CustomerQuestion, data["question_id"])
            assert q.status == "pending"
            assert q.ai_answer is None

# 3. Null AI response
def test_03_null_ai_response(client):
    shop, token = _setup_shop_and_session(client, "null-shop-3", "alice3@test.com", "Gamma Tech")
    headers = {"X-Customer-Session": token}

    with patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
        with patch.object(AIService, "_call_gemini", return_value={"can_answer": True, "answer": None, "provider": "gemini"}):
            res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
                "message": "Tell me about your phones"
            })
            assert res.status_code == 200
            data = res.get_json()["data"]

            assert data["answer"] == FALLBACK_MESSAGE
            assert data["can_answer"] is False
            assert data["status"] == "pending"

# 4. Malformed AI response (metadata-only or only whitespace)
def test_04_malformed_ai_response(client):
    shop, token = _setup_shop_and_session(client, "malformed-shop-4", "alice4@test.com", "Delta Tech")
    headers = {"X-Customer-Session": token}

    with patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
        # Case A: whitespace only
        with patch.object(AIService, "_call_gemini", return_value={"can_answer": True, "answer": "   \n\t  ", "provider": "gemini"}):
            res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
                "message": "Tell me about your phones"
            })
            assert res.status_code == 200
            assert res.get_json()["data"]["answer"] == FALLBACK_MESSAGE

        # Case B: internal metadata only like "[Entry 1 - Products] Category: Products"
        with patch.object(AIService, "_call_gemini", return_value={"can_answer": True, "answer": "[Entry 1 - Products] Category: Products", "provider": "gemini"}):
            res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
                "message": "Tell me about your phones"
            })
            assert res.status_code == 200
            data = res.get_json()["data"]
            assert data["answer"] == FALLBACK_MESSAGE
            assert data["can_answer"] is False

# 5. Irrelevant knowledge-base match (Asking for address when shop has only timings & products)
def test_05_irrelevant_knowledge_base_match(client):
    shop, token = _setup_shop_and_session(client, "irrelevant-shop-5", "alice5@test.com", "Epsilon Tech")
    headers = {"X-Customer-Session": token}

    # "What is your shop address?" must not return timings or products
    res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "What is your shop address?"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == FALLBACK_MESSAGE
    assert "9:00 AM" not in data["answer"]

# 6. Relevant knowledge-base match (Intent understanding with synonyms)
def test_06_relevant_knowledge_base_match(client):
    shop, token = _setup_shop_and_session(client, "relevant-shop-6", "alice6@test.com", "Zeta Tech")
    headers = {"X-Customer-Session": token}

    # "I want a mobile phone" matches "smartphones"
    res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "I want a mobile phone."
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["can_answer"] is True
    assert data["status"] == "answered"
    assert "Samsung" in data["answer"] or "Apple" in data["answer"] or "smartphones" in data["answer"]
    assert "Which brand or model" in data["answer"]

# 7. Unknown customer question
def test_07_unknown_customer_question(client):
    shop, token = _setup_shop_and_session(client, "unknown-shop-7", "alice7@test.com", "Eta Tech")
    headers = {"X-Customer-Session": token}

    res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "Do you sell supersonic airplane engines?"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["can_answer"] is False
    assert data["status"] == "pending"
    assert data["answer"] == FALLBACK_MESSAGE

# 8. AI provider timeout
def test_08_ai_provider_timeout(client):
    shop, token = _setup_shop_and_session(client, "timeout-shop-8", "alice8@test.com", "Theta Tech")
    headers = {"X-Customer-Session": token}

    with patch.dict(client.application.config, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
        with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out")):
            res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
                "message": "What time do you open?"
            })
            assert res.status_code == 200
            data = res.get_json()["data"]
            # Must not crash; returns safe fallback
            assert data["answer"] == FALLBACK_MESSAGE
            assert data["can_answer"] is False
            assert data["status"] == "pending"

# 9. Duplicate customer submission
def test_09_duplicate_customer_submission(client):
    shop, token = _setup_shop_and_session(client, "dupe-shop-9", "alice9@test.com", "Iota Tech")
    headers = {"X-Customer-Session": token}

    # First send
    res1 = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "What time do you open?"
    })
    assert res1.status_code == 200
    msg_id1 = res1.get_json()["data"]["message_id"]

    # Immediate duplicate send
    res2 = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "What time do you open?"
    })
    assert res2.status_code == 200
    msg_id2 = res2.get_json()["data"]["message_id"]

    # Deduplicated to same message
    assert msg_id1 == msg_id2

# 10. Feedback buttons on valid answers
def test_10_feedback_buttons_on_valid_answers(client):
    shop, token = _setup_shop_and_session(client, "feedback-shop-10", "alice10@test.com", "Kappa Tech")
    headers = {"X-Customer-Session": token}

    chat_res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "What time do you open?"
    })
    assert chat_res.status_code == 200
    q_id = chat_res.get_json()["data"]["question_id"]

    # Submit Good Answer
    fb_res = client.post(f"/api/public/shop/{shop.slug}/feedback", headers=headers, json={
        "question_id": q_id,
        "feedback_type": "good"
    })
    assert fb_res.status_code == 200
    fb_data = fb_res.get_json()["data"]
    assert fb_data["feedback_type"] == "good"
    assert fb_data["question_id"] == q_id

# 11. Feedback buttons hidden on empty or pending responses
def test_11_feedback_buttons_hidden_on_pending(client):
    shop, token = _setup_shop_and_session(client, "hidden-fb-shop-11", "alice11@test.com", "Lambda Tech")
    headers = {"X-Customer-Session": token}

    # Ask unknown question -> triggers pending fallback
    chat_res = client.post(f"/api/public/shop/{shop.slug}/chat", headers=headers, json={
        "message": "Where are you located in New York City?"
    })
    assert chat_res.status_code == 200
    q_id = chat_res.get_json()["data"]["question_id"]

    # Attempting to submit feedback on a pending fallback message must be rejected with 400
    fb_res = client.post(f"/api/public/shop/{shop.slug}/feedback", headers=headers, json={
        "question_id": q_id,
        "feedback_type": "good"
    })
    assert fb_res.status_code == 400
    assert "Only eligible AI-generated answers can be rated" in fb_res.get_json()["message"]

# 12. Multi-tenant knowledge isolation
def test_12_multi_tenant_knowledge_isolation(client):
    # Shop A sells mobile phones
    shop_a, token_a = _setup_shop_and_session(client, "shop-a-phones", "cust_a@test.com", "Shop A Phones")

    # Shop B sells clothes
    user_b = User(email="owner_b@test.com", full_name="Shop B Owner", password_hash="dummy_hash")
    db.session.add(user_b)
    db.session.flush()

    shop_b = Shop(owner_id=user_b.id, shop_name="Shop B Clothes", slug="shop-b-clothes")
    db.session.add(shop_b)
    db.session.flush()

    kb_b = KnowledgeBase(
        shop_id=shop_b.id,
        category="Products",
        title="Fashion Wear",
        content="We sell women's sarees, designer kurtas, and silk dresses."
    )
    db.session.add(kb_b)
    db.session.commit()

    res_b_sess = client.post(f"/api/public/shop/{shop_b.slug}/session", json={
        "first_name": "Bob", "last_name": "Brown", "email": "bob@test.com"
    })
    token_b = res_b_sess.get_json()["data"]["session_token"]

    # Customer at Shop B asks about dresses
    res_b = client.post(f"/api/public/shop/{shop_b.slug}/chat", headers={"X-Customer-Session": token_b}, json={
        "message": "Do you sell silk dresses?"
    })
    assert res_b.status_code == 200
    assert res_b.get_json()["data"]["can_answer"] is True
    assert "sarees" in res_b.get_json()["data"]["answer"] or "silk dresses" in res_b.get_json()["data"]["answer"]

    # Customer at Shop A asks about dresses -> Shop A has NO knowledge about dresses
    res_a = client.post(f"/api/public/shop/{shop_a.slug}/chat", headers={"X-Customer-Session": token_a}, json={
        "message": "Do you sell silk dresses?"
    })
    assert res_a.status_code == 200
    # Must NOT leak Shop B's clothes collection! Must fallback to pending for Shop A
    assert res_a.get_json()["data"]["can_answer"] is False
    assert res_a.get_json()["data"]["answer"] == FALLBACK_MESSAGE

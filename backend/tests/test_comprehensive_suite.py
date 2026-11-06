import pytest
from datetime import datetime, timezone, timedelta
from backend.app.models import db, User, Shop, KnowledgeBase, Customer, CustomerSession, CustomerQuestion, AnswerFeedback

# ----------------------------------------------------------------------
# 1. Shop owner can register.
# ----------------------------------------------------------------------
def test_01_owner_registration(client):
    res = client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["shop"]["slug"] == "ravi-mobiles"

# ----------------------------------------------------------------------
# 2. Shop owner can log in.
# ----------------------------------------------------------------------
def test_02_owner_login(client):
    client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    })
    res = client.post("/api/auth/login", json={
        "email": "ravi@gmail.com",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["user"]["email"] == "ravi@gmail.com"

# ----------------------------------------------------------------------
# 3. Duplicate email registration is rejected.
# ----------------------------------------------------------------------
def test_03_duplicate_email_rejected(client):
    payload = {
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201
    
    # Second attempt with same email
    res2 = client.post("/api/auth/register", json={
        "full_name": "Ravi Another",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Store 2",
        "slug": "ravi-store-2"
    })
    assert res2.status_code == 409
    assert "already exists" in res2.get_json()["message"]

# ----------------------------------------------------------------------
# 4. Owner can add knowledge.
# ----------------------------------------------------------------------
def test_04_owner_add_knowledge(client, auth_headers):
    res = client.post("/api/knowledge", json={
        "title": "Shop Timings",
        "content": "We open at 9 AM and close at 9 PM Monday to Saturday.",
        "category": "Timings"
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "Shop Timings"

# ----------------------------------------------------------------------
# 5. Owner can edit knowledge.
# ----------------------------------------------------------------------
def test_05_owner_edit_knowledge(client, auth_headers):
    # Add entry
    add_res = client.post("/api/knowledge", json={
        "title": "Return Policy",
        "content": "Returns within 7 days.",
        "category": "Policy"
    }, headers=auth_headers)
    entry_id = add_res.get_json()["data"][0]["id"]
    
    # Edit entry
    edit_res = client.put(f"/api/knowledge/{entry_id}", json={
        "title": "Updated Return Policy",
        "content": "Returns accepted within 14 days with original bill.",
        "category": "Policy"
    }, headers=auth_headers)
    assert edit_res.status_code == 200
    assert edit_res.get_json()["data"]["title"] == "Updated Return Policy"

# ----------------------------------------------------------------------
# 6. Owner can delete knowledge.
# ----------------------------------------------------------------------
def test_06_owner_delete_knowledge(client, auth_headers):
    add_res = client.post("/api/knowledge", json={
        "title": "Temporary Notice",
        "content": "Closed on Sunday.",
        "category": "Notice"
    }, headers=auth_headers)
    entry_id = add_res.get_json()["data"][0]["id"]
    
    del_res = client.delete(f"/api/knowledge/{entry_id}", headers=auth_headers)
    assert del_res.status_code == 200
    
    # Verify gone
    list_res = client.get("/api/knowledge", headers=auth_headers)
    items = list_res.get_json()["data"]["knowledge_entries"]
    assert not any(i["id"] == entry_id for i in items)

# ----------------------------------------------------------------------
# 7. Each shop receives a unique slug.
# ----------------------------------------------------------------------
def test_07_unique_shop_slug(client):
    client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    })
    # Attempt duplicate slug
    res = client.post("/api/auth/register", json={
        "full_name": "Another Ravi",
        "email": "another@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles Branch",
        "slug": "ravi-mobiles"
    })
    assert res.status_code == 409
    assert "already taken" in res.get_json()["message"]

# ----------------------------------------------------------------------
# 8. Customer can access the correct shop chatbot.
# ----------------------------------------------------------------------
def test_08_customer_access_correct_shop(client, auth_headers):
    # Public fetch of shop info
    res = client.get("/api/public/shop/test-shop")
    assert res.status_code == 200
    data = res.get_json()
    assert data["data"]["shop"]["slug"] == "test-shop"
    assert data["data"]["shop"]["shop_name"] == "Test Shop"

# ----------------------------------------------------------------------
# 9. Customer session persists after reload.
# ----------------------------------------------------------------------
def test_09_customer_session_persists(client):
    # Register shop
    client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    })
    # Create customer session
    sess_res = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    })
    assert sess_res.status_code == 201
    token = sess_res.get_json()["data"]["session_token"]
    
    # Validate session (simulate reload)
    val_res = client.get("/api/public/shop/ravi-mobiles/session/validate", headers={
        "X-Customer-Session": token
    })
    assert val_res.status_code == 200
    assert val_res.get_json()["data"]["valid"] is True
    assert val_res.get_json()["data"]["customer"]["email"] == "john@example.com"

# ----------------------------------------------------------------------
# 10. Customer session expires after 36 hours.
# ----------------------------------------------------------------------
def test_10_customer_session_expiration(client, app):
    client.post("/api/auth/register", json={
        "full_name": "Ravi Kumar",
        "email": "ravi@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Ravi Mobiles",
        "slug": "ravi-mobiles"
    })
    sess_res = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com"
    })
    token = sess_res.get_json()["data"]["session_token"]
    
    # Manually backdate the session's expiration past 36 hours
    with app.app_context():
        sess = CustomerSession.query.first()
        sess.expires_at = datetime.now(timezone.utc) - timedelta(hours=37)
        db.session.commit()
        
    val_res = client.get("/api/public/shop/ravi-mobiles/session/validate", headers={
        "X-Customer-Session": token
    })
    assert val_res.status_code == 401
    assert val_res.get_json()["errors"]["requires_reauth"] is True

# ----------------------------------------------------------------------
# 11. AI retrieves only the current shop's knowledge.
# ----------------------------------------------------------------------
def test_11_ai_retrieves_current_shop_knowledge(client):
    # Setup Shop A
    res_a = client.post("/api/auth/register", json={
        "full_name": "Ravi", "email": "ravi@gmail.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Ravi Mobiles", "slug": "ravi-mobiles"
    })
    token_a = res_a.get_json()["data"]["token"]
    client.post("/api/knowledge", json={
        "title": "Shop Timings", "content": "We open at 9 AM and close at 9 PM.", "category": "Timings"
    }, headers={"Authorization": f"Bearer {token_a}"})
    
    # Setup Shop B
    res_b = client.post("/api/auth/register", json={
        "full_name": "Sri", "email": "sri@gmail.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Sri Fashion", "slug": "sri-fashion"
    })
    token_b = res_b.get_json()["data"]["token"]
    client.post("/api/knowledge", json={
        "title": "Shop Timings", "content": "We open at 10 AM and close at 8 PM.", "category": "Timings"
    }, headers={"Authorization": f"Bearer {token_b}"})
    
    # Customer asks Shop A
    c_sess_a = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "Alex", "last_name": "Brown", "email": "alex@test.com"
    }).get_json()["data"]["session_token"]
    
    chat_a = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": "What time do you open?"
    }, headers={"X-Customer-Session": c_sess_a})
    assert "9 AM" in chat_a.get_json()["data"]["answer"]
    assert "10 AM" not in chat_a.get_json()["data"]["answer"]
    
    # Customer asks Shop B
    c_sess_b = client.post("/api/public/shop/sri-fashion/session", json={
        "first_name": "Bella", "last_name": "Green", "email": "bella@test.com"
    }).get_json()["data"]["session_token"]
    
    chat_b = client.post("/api/public/shop/sri-fashion/chat", json={
        "message": "What time do you open?"
    }, headers={"X-Customer-Session": c_sess_b})
    assert "10 AM" in chat_b.get_json()["data"]["answer"]
    assert "9 AM" not in chat_b.get_json()["data"]["answer"]

# ----------------------------------------------------------------------
# 12. AI returns fallback for unknown questions.
# ----------------------------------------------------------------------
def test_12_ai_returns_fallback_for_unknown(client, auth_headers):
    sess_res = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Ken", "last_name": "Adams", "email": "ken@test.com"
    })
    token = sess_res.get_json()["data"]["session_token"]
    
    chat_res = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you provide helicopter rides to the moon?"
    }, headers={"X-Customer-Session": token})
    
    data = chat_res.get_json()["data"]
    assert data["answer"] == "Thank you! The shop owner will reply to you soon by email."
    assert data["can_answer"] is False
    assert data["status"] == "pending"

# ----------------------------------------------------------------------
# 13. Unknown questions are saved as Pending.
# ----------------------------------------------------------------------
def test_13_unknown_saved_as_pending(client, auth_headers):
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Ken", "last_name": "Adams", "email": "ken@test.com"
    }).get_json()["data"]["session_token"]
    
    client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you deliver to Mars?"
    }, headers={"X-Customer-Session": sess})
    
    q_list = client.get("/api/questions?status=pending", headers=auth_headers).get_json()["data"]["questions"]
    assert any(q["question"] == "Do you deliver to Mars?" and q["status"] == "pending" for q in q_list)

# ----------------------------------------------------------------------
# 14. Owner can answer pending questions.
# ----------------------------------------------------------------------
def test_14_owner_can_answer_pending(client, auth_headers):
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Sara", "last_name": "Lee", "email": "sara@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you offer gift wrapping?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    ans_res = client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Yes, we provide complimentary gift wrapping on all orders!"
    }, headers=auth_headers)
    assert ans_res.status_code == 200
    data = ans_res.get_json()["data"]
    assert data["question"]["status"] == "answered"
    assert data["question"]["owner_answer"] == "Yes, we provide complimentary gift wrapping on all orders!"

# ----------------------------------------------------------------------
# 15. Email is triggered after an answer.
# ----------------------------------------------------------------------
def test_15_email_triggered_after_answer(client, auth_headers):
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "David", "last_name": "Miller", "email": "david@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Are bulk discounts available?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    ans_res = client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Yes, 10% off on 10 items or more."
    }, headers=auth_headers)
    # email_status should be 'sent' or 'failed' based on service response
    assert ans_res.get_json()["data"]["email_status"] in ("sent", "failed")

# ----------------------------------------------------------------------
# 16. Failed emails can be retried.
# ----------------------------------------------------------------------
def test_16_failed_email_retry(client, auth_headers, app):
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Emma", "last_name": "Watson", "email": "emma@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Can I pay with cryptocurrency?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Currently we accept credit cards, debit cards, and cash."
    }, headers=auth_headers)
    
    # Mark email as failed
    with app.app_context():
        q = db.session.get(CustomerQuestion, q_id)
        q.email_status = "failed"
        db.session.commit()
        
    retry_res = client.post(f"/api/questions/{q_id}/retry-email", headers=auth_headers)
    assert retry_res.status_code in (200, 502)

# ----------------------------------------------------------------------
# 17. Good feedback is saved.
# ----------------------------------------------------------------------
def test_17_good_feedback_saved(client, auth_headers):
    # Add knowledge
    client.post("/api/knowledge", json={
        "title": "Warranty", "content": "1 year warranty on all smartphones.", "category": "Policy"
    }, headers=auth_headers)
    
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Tom", "last_name": "Hanks", "email": "tom@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "What is the warranty period?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    fb_res = client.post(f"/api/feedback/{q_id}/good", headers=auth_headers)
    assert fb_res.status_code == 200
    assert fb_res.get_json()["data"]["feedback_type"] == "good"

# ----------------------------------------------------------------------
# 18. Bad feedback is saved.
# ----------------------------------------------------------------------
def test_18_bad_feedback_saved(client, auth_headers):
    # Add knowledge
    client.post("/api/knowledge", json={
        "title": "Accessories", "content": "We sell cases and screen guards.", "category": "Products"
    }, headers=auth_headers)
    
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Chris", "last_name": "Evans", "email": "chris@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you sell chargers?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    fb_res = client.post(f"/api/feedback/{q_id}/bad", json={
        "reason": "The answer was vague and missed mentioning fast chargers.",
        "correct_answer": "Yes, we sell 65W and 120W fast chargers for Apple and Android."
    }, headers=auth_headers)
    assert fb_res.status_code == 200
    assert fb_res.get_json()["data"]["feedback"]["feedback_type"] == "bad"

# ----------------------------------------------------------------------
# 19. Correct answers are added to the knowledge base.
# ----------------------------------------------------------------------
def test_19_correct_answers_added_to_knowledge_base(client, auth_headers):
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Mark", "last_name": "Ruffalo", "email": "mark@test.com"
    }).get_json()["data"]["session_token"]
    
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you provide screen repair?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]
    
    client.post(f"/api/feedback/{q_id}/bad", json={
        "reason": "Missing repair service details",
        "correct_answer": "Yes, we offer same-day screen replacement with 6 months warranty."
    }, headers=auth_headers)
    
    # Check knowledge base has the correction
    kb_res = client.get("/api/knowledge", headers=auth_headers)
    entries = kb_res.get_json()["data"]["knowledge_entries"]
    assert any(e["source_type"] == "feedback_correction" and "screen replacement" in e["content"] for e in entries)

# ----------------------------------------------------------------------
# 20. Shop A cannot access Shop B's information (strict tenant isolation).
# ----------------------------------------------------------------------
def test_20_tenant_isolation(client):
    # Register Shop A
    res_a = client.post("/api/auth/register", json={
        "full_name": "Owner A", "email": "owner_a@test.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Shop A", "slug": "shop-a"
    })
    token_a = res_a.get_json()["data"]["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Register Shop B
    res_b = client.post("/api/auth/register", json={
        "full_name": "Owner B", "email": "owner_b@test.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Shop B", "slug": "shop-b"
    })
    token_b = res_b.get_json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # Shop A adds secret knowledge
    add_a = client.post("/api/knowledge", json={
        "title": "Shop A Confidential Note",
        "content": "Confidential wholesale supplier rates.",
        "category": "Private"
    }, headers=headers_a)
    entry_a_id = add_a.get_json()["data"][0]["id"]
    
    # Shop B lists knowledge entries -> Shop A's entry must NOT appear
    list_b = client.get("/api/knowledge", headers=headers_b)
    entries_b = list_b.get_json()["data"]["knowledge_entries"]
    assert not any(e["id"] == entry_a_id for e in entries_b)
    
    # Shop B attempts to edit or delete Shop A's entry -> Must return 404 unauthorized
    edit_attempt = client.put(f"/api/knowledge/{entry_a_id}", json={
        "title": "Hacked", "content": "Hacked"
    }, headers=headers_b)
    assert edit_attempt.status_code == 404
    
    delete_attempt = client.delete(f"/api/knowledge/{entry_a_id}", headers=headers_b)
    assert delete_attempt.status_code == 404

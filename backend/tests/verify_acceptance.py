import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.models import db, User, Shop, KnowledgeBase, CustomerQuestion
from backend.app.utils.security import check_password

def run_verification():
    app = create_app()
    with app.app_context():
        print("="*70)
        print("VERIFICATION STEP 1: DEMO ACCOUNTS IN DATABASE")
        print("="*70)

        # Check Shop A User
        user_a = User.query.filter_by(email="ravi@gmail.com").first()
        assert user_a is not None, "Shop A user (ravi@gmail.com) not found in DB!"
        assert check_password("password123", user_a.password_hash), "Shop A password check failed!"
        shop_a = Shop.query.filter_by(owner_id=user_a.id).first()
        assert shop_a is not None, "Shop A not found for user!"
        assert shop_a.slug == "ravi-mobiles", f"Expected slug 'ravi-mobiles', got '{shop_a.slug}'"
        print(f"Shop A Owner: {user_a.full_name} ({user_a.email}) - Login Verified [PASS]")
        print(f"Shop A Details: {shop_a.shop_name} (slug: {shop_a.slug}) - Verified [PASS]")

        # Check Shop B User
        user_b = User.query.filter_by(email="sri@gmail.com").first()
        assert user_b is not None, "Shop B user (sri@gmail.com) not found in DB!"
        assert check_password("password123", user_b.password_hash), "Shop B password check failed!"
        shop_b = Shop.query.filter_by(owner_id=user_b.id).first()
        assert shop_b is not None, "Shop B not found for user!"
        assert shop_b.slug == "sri-fashion", f"Expected slug 'sri-fashion', got '{shop_b.slug}'"
        print(f"Shop B Owner: {user_b.full_name} ({user_b.email}) - Login Verified [PASS]")
        print(f"Shop B Details: {shop_b.shop_name} (slug: {shop_b.slug}) - Verified [PASS]")

        # Check Knowledge Base entries for both shops
        kb_a = KnowledgeBase.query.filter_by(shop_id=shop_a.id).all()
        kb_b = KnowledgeBase.query.filter_by(shop_id=shop_b.id).all()
        print(f"Shop A Knowledge Base entries: {len(kb_a)}")
        for e in kb_a:
            print(f"   - [{e.category}] {e.title}: {e.content[:60]}...")
        assert len(kb_a) >= 3, f"Expected at least 3 KB entries for Shop A, found {len(kb_a)}"

        print(f"Shop B Knowledge Base entries: {len(kb_b)}")
        for e in kb_b:
            print(f"   - [{e.category}] {e.title}: {e.content[:60]}...")
        assert len(kb_b) >= 3, f"Expected at least 3 KB entries for Shop B, found {len(kb_b)}"

        print("="*70)
        print("VERIFICATION STEP 2: REQUIREMENT 1.A - AUTOMATIC KB LEARNING WORKFLOW")
        print("="*70)

    client = app.test_client()

    # 1. Login Shop A
    login_res = client.post("/api/auth/login", json={
        "email": "ravi@gmail.com",
        "password": "password123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.get_json()}"
    token_a = login_res.get_json()["data"]["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("1. Logged into Shop A via API: Token received [PASS]")

    # 2. Public customer link check for Shop A and Shop B
    res_pub_a = client.get("/api/public/shop/ravi-mobiles")
    assert res_pub_a.status_code == 200
    assert res_pub_a.get_json()["data"]["shop"]["shop_name"] == "Ravi Mobiles"
    print(f"2. Shop A Public Customer Link (/s/ravi-mobiles) HTTP 200 verified [PASS]")

    res_pub_b = client.get("/api/public/shop/sri-fashion")
    assert res_pub_b.status_code == 200
    assert res_pub_b.get_json()["data"]["shop"]["shop_name"] == "Sri Fashion"
    print(f"2b. Shop B Public Customer Link (/s/sri-fashion) HTTP 200 verified [PASS]")

    # 3. Customer starts session on Shop A
    sess_res = client.post("/api/public/shop/ravi-mobiles/session", json={
        "first_name": "Verification",
        "last_name": "Customer",
        "email": "verify.customer@example.com"
    })
    assert sess_res.status_code == 201
    cust_token = sess_res.get_json()["data"]["session_token"]
    cust_headers = {"X-Customer-Session": cust_token}
    print("3. Customer session created for Shop A [PASS]")

    # 4. Ask an unknown question in Shop A
    unknown_question = "Do you provide express 2-hour home delivery?"
    chat1 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": unknown_question
    }, headers=cust_headers)
    assert chat1.status_code == 200
    data1 = chat1.get_json()["data"]
    print(f"4. Customer asked: '{unknown_question}'")
    print(f"   AI response: '{data1['answer']}'")
    assert data1["can_answer"] is False
    assert data1["status"] == "pending"
    assert "Thank you! The shop owner will reply to you soon by email." in data1["answer"]
    question_id = data1["question_id"]
    print(f"   Verified: Status is 'pending', question_id={question_id} [PASS]")

    # 5. Confirm it appears in Owner's Pending list
    pending_res = client.get("/api/questions?status=pending", headers=headers_a)
    assert pending_res.status_code == 200
    pending_questions = pending_res.get_json()["data"]["questions"]
    matching_q = [q for q in pending_questions if q["id"] == question_id]
    assert len(matching_q) == 1, f"Question #{question_id} not found in pending list!"
    print(f"5. Owner retrieved pending list: Question #{question_id} present in Pending [PASS]")

    # 6. Answer it as the owner
    owner_answer_text = "Yes, we provide express 2-hour home delivery within city limits for a nominal 50 rupee fee."
    ans_res = client.post(f"/api/questions/{question_id}/answer", json={
        "answer": owner_answer_text
    }, headers=headers_a)
    assert ans_res.status_code == 200
    ans_data = ans_res.get_json()["data"]
    assert ans_data["question"]["status"] == "answered"
    print(f"6. Owner submitted answer: '{owner_answer_text}' [PASS]")

    # 7. Inspect database and confirm knowledge entry was saved
    with app.app_context():
        db_q = db.session.get(CustomerQuestion, question_id)
        assert db_q.status == "answered"
        assert db_q.owner_answer == owner_answer_text
        print(f"7a. Database Question #{question_id}: status='{db_q.status}', owner_answer saved [PASS]")

        learned_kb = KnowledgeBase.query.filter_by(
            shop_id=shop_a.id,
            source_type="pending_answered"
        ).filter(KnowledgeBase.content.like(f"%{unknown_question}%")).first()
        assert learned_kb is not None, "Learned knowledge entry not found in database!"
        print(f"7b. Database KnowledgeBase Entry #{learned_kb.id}:")
        print(f"    Title: '{learned_kb.title}'")
        print(f"    Category: '{learned_kb.category}'")
        print(f"    Source Type: '{learned_kb.source_type}'")
        print(f"    Content:\n    {learned_kb.content}")
        assert "express 2-hour home delivery" in learned_kb.content
        assert learned_kb.shop_id == shop_a.id
        print("    Verified: Correct shop_id, question, answer, and metadata persisted [PASS]")

    # 8. Ask the exact same question again in Shop A
    chat2 = client.post("/api/public/shop/ravi-mobiles/chat", json={
        "message": unknown_question
    }, headers=cust_headers)
    assert chat2.status_code == 200
    data2 = chat2.get_json()["data"]
    print(f"8. Customer asked again: '{unknown_question}'")
    print(f"   AI response: '{data2['answer']}'")
    assert data2["can_answer"] is True
    assert data2["status"] == "answered"
    assert "2-hour" in data2["answer"].lower() or "express" in data2["answer"].lower()
    print("   Verified: AI immediately returned the saved owner-approved answer [PASS]")

    # 9. Ask the same question in Shop B and confirm Shop A's answer is NOT exposed
    sess_b_res = client.post("/api/public/shop/sri-fashion/session", json={
        "first_name": "ShopB",
        "last_name": "Tester",
        "email": "shopb.tester@example.com"
    })
    assert sess_b_res.status_code == 201
    cust_b_token = sess_b_res.get_json()["data"]["session_token"]
    cust_b_headers = {"X-Customer-Session": cust_b_token}

    chat_b = client.post("/api/public/shop/sri-fashion/chat", json={
        "message": unknown_question
    }, headers=cust_b_headers)
    assert chat_b.status_code == 200
    data_b = chat_b.get_json()["data"]
    print(f"9. Customer asked Shop B: '{unknown_question}'")
    print(f"   Shop B AI response: '{data_b['answer']}'")
    assert data_b["can_answer"] is False
    assert data_b["status"] == "pending"
    assert "express 2-hour home delivery" not in data_b["answer"]
    assert "Thank you! The shop owner will reply to you soon by email." in data_b["answer"]
    print("   Verified: Shop B has ZERO access to Shop A's learned answer (Strict Tenant Isolation) [PASS]")

    print("="*70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY WITH ZERO ERRORS!")
    print("="*70)

if __name__ == "__main__":
    run_verification()

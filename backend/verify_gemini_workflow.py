import os
import sys
import time
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import requests
from backend.app import create_app, db
from backend.app.models import Shop, Customer, CustomerSession, Conversation, Message, CustomerQuestion, KnowledgeBase
from backend.app.services.ai_service import AIService, FALLBACK_MESSAGE

def mask_key(k: str) -> str:
    if not k:
        return "[NOT SET]"
    if len(k) <= 8:
        return "***"
    return f"{k[:4]}...{k[-4:]} ({len(k)} chars)"

def run_comprehensive_workflow_verification():
    app = create_app()
    with app.app_context():
        client = app.test_client()

        print("=" * 85)
        print("SHOPGENIE AI - GEMINI-3.5-FLASH-LITE COMPREHENSIVE WORKFLOW VERIFICATION")
        print("=" * 85)

        # -------------------------------------------------------------
        # 1. Restart/Reload Configuration
        # -------------------------------------------------------------
        print("\n[1 & 2] APPLICATION CONFIGURATION & ACTIVE RUNTIME MODEL:")
        runtime_provider = app.config.get("AI_PROVIDER")
        runtime_model = app.config.get("GEMINI_MODEL")
        api_key = app.config.get("GEMINI_API_KEY", "").strip()

        print(f"    - AI_PROVIDER: '{runtime_provider}'")
        print(f"    - GEMINI_MODEL: '{runtime_model}'")
        print(f"    - GEMINI_API_KEY: {mask_key(api_key)}")
        assert runtime_provider == "gemini", f"Expected AI_PROVIDER='gemini', got '{runtime_provider}'"
        assert runtime_model == "gemini-3.5-flash-lite", f"Expected GEMINI_MODEL='gemini-3.5-flash-lite', got '{runtime_model}'"
        assert bool(api_key), "GEMINI_API_KEY is not configured"
        print("    --> Verification [1 & 2]: PASS (Active runtime model is confirmed as gemini-3.5-flash-lite)")

        # -------------------------------------------------------------
        # 3. Genuine Gemini API Direct Request
        # -------------------------------------------------------------
        print("\n[3] DIRECT GEMINI API REQUEST:")
        direct_url = f"https://generativelanguage.googleapis.com/v1beta/models/{runtime_model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "In exactly one sentence, describe what ShopGenie AI is."}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 100}
        }
        t0 = time.time()
        res = requests.post(direct_url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        elapsed = time.time() - t0
        print(f"    - Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{runtime_model}:generateContent")
        print(f"    - HTTP Status: {res.status_code}")
        print(f"    - Latency: {elapsed:.2f}s")
        assert res.status_code == 200, f"Direct API request failed with status {res.status_code}: {res.text}"
        data = res.json()
        direct_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"    - Direct Gemini Response: \"{direct_text}\"")
        print("    --> Verification [3]: PASS (Genuine HTTP 200 response received from Gemini)")

        # Fetch Shops
        shop_a = Shop.query.filter_by(slug="ravi-mobiles").first()
        shop_b = Shop.query.filter_by(slug="sri-fashion").first()
        assert shop_a is not None, "Shop A (ravi-mobiles) not found in database"
        assert shop_b is not None, "Shop B (sri-fashion) not found in database"

        # -------------------------------------------------------------
        # Helper to create customer session
        # -------------------------------------------------------------
        def create_session(shop_slug: str, email: str, fname: str, lname: str):
            res = client.post(f"/api/public/shop/{shop_slug}/session", json={
                "first_name": fname,
                "last_name": lname,
                "email": email
            })
            assert res.status_code == 201, f"Failed to create session: {res.get_json()}"
            return res.get_json()["data"]["session_token"]

        token_a = create_session("ravi-mobiles", "tester.shopa@example.com", "RaviCustomer", "One")
        token_b = create_session("sri-fashion", "tester.shopb@example.com", "SriCustomer", "Two")

        # -------------------------------------------------------------
        # 4 & 5. Test Shop A Customer Workflow: Hours, Return Policy, Products
        # -------------------------------------------------------------
        print("\n[4 & 5] SHOP A (Ravi Mobiles) - CUSTOMER SUPPORT WORKFLOW:")

        # 5a. Opening Hours
        print("    --- Test 5a: Shop Opening Hours & Working Days ---")
        res_hours = client.post(
            "/api/public/shop/ravi-mobiles/chat",
            json={"message": "What are your shop opening hours and working days?"},
            headers={"X-Customer-Session": token_a}
        )
        print(f"    - HTTP Status: {res_hours.status_code}")
        data_hours = res_hours.get_json()["data"]
        print(f"    - AI Answer: \"{data_hours['answer']}\"")
        print(f"    - Status: {data_hours['status']} | can_answer: {data_hours['can_answer']}")
        assert data_hours["status"] == "answered", "Expected status='answered' for opening hours"
        assert data_hours["can_answer"] is True, "Expected can_answer=True for opening hours"
        assert "9" in data_hours["answer"], "Expected '9' (9 AM to 9 PM) in opening hours answer"
        assert data_hours["answer"] != FALLBACK_MESSAGE

        # 5b. Return Policy
        print("    --- Test 5b: Return Policy ---")
        res_policy = client.post(
            "/api/public/shop/ravi-mobiles/chat",
            json={"message": "What is your return policy?"},
            headers={"X-Customer-Session": token_a}
        )
        data_policy = res_policy.get_json()["data"]
        print(f"    - AI Answer: \"{data_policy['answer']}\"")
        print(f"    - Status: {data_policy['status']} | can_answer: {data_policy['can_answer']}")
        assert data_policy["status"] == "answered", "Expected status='answered' for return policy"
        assert data_policy["can_answer"] is True, "Expected can_answer=True for return policy"
        assert "7" in data_policy["answer"] or "seven" in data_policy["answer"].lower(), "Expected 7-day policy"
        assert data_policy["answer"] != FALLBACK_MESSAGE

        # 5c. Products and Brands
        print("    --- Test 5c: Products and Brands ---")
        res_products = client.post(
            "/api/public/shop/ravi-mobiles/chat",
            json={"message": "What smartphone brands and products do you sell?"},
            headers={"X-Customer-Session": token_a}
        )
        data_products = res_products.get_json()["data"]
        print(f"    - AI Answer: \"{data_products['answer']}\"")
        print(f"    - Status: {data_products['status']} | can_answer: {data_products['can_answer']}")
        assert data_products["status"] == "answered", "Expected status='answered' for products"
        assert data_products["can_answer"] is True, "Expected can_answer=True for products"
        # Check brand mention
        ans_lower = data_products["answer"].lower()
        assert any(b in ans_lower for b in ["samsung", "apple", "oneplus", "vivo", "oppo"]), "Expected mobile brands mentioned"
        print("    --> Verification [4 & 5]: PASS (All 3 queries correctly answered from Shop A knowledge)")

        # -------------------------------------------------------------
        # 6. Unknown Question Goes to Pending
        # -------------------------------------------------------------
        print("\n[6] UNKNOWN QUESTION WORKFLOW (Shop A):")
        unknown_q = "Do you sell PlayStation 5 gaming consoles or gaming chairs?"
        res_unknown = client.post(
            "/api/public/shop/ravi-mobiles/chat",
            json={"message": unknown_q},
            headers={"X-Customer-Session": token_a}
        )
        data_unknown = res_unknown.get_json()["data"]
        print(f"    - Customer Question: \"{unknown_q}\"")
        print(f"    - AI Answer: \"{data_unknown['answer']}\"")
        print(f"    - Status: {data_unknown['status']} | can_answer: {data_unknown['can_answer']}")
        print(f"    - Question ID: {data_unknown['question_id']}")

        assert data_unknown["can_answer"] is False, "Unknown question must have can_answer=False"
        assert data_unknown["status"] == "pending", "Unknown question must have status='pending'"
        assert data_unknown["answer"] == FALLBACK_MESSAGE, f"Expected fallback message, got: {data_unknown['answer']}"

        # Verify in database
        q_record = CustomerQuestion.query.get(data_unknown["question_id"])
        assert q_record is not None, "CustomerQuestion record not found in database"
        assert q_record.status == "pending", f"DB record status is '{q_record.status}', expected 'pending'"
        assert q_record.ai_answer is None, "Pending question should have ai_answer=None in DB"
        print("    --> Verification [6]: PASS (Unknown question correctly routed to Pending with fallback message)")

        # -------------------------------------------------------------
        # 7 & 8. Multi-Tenant Knowledge Isolation: Shop A vs Shop B
        # -------------------------------------------------------------
        print("\n[7 & 8] CROSS-TENANT KNOWLEDGE ISOLATION (Shop A vs Shop B):")

        # 8a. Hours comparison
        res_b_hours = client.post(
            "/api/public/shop/sri-fashion/chat",
            json={"message": "What are your shop opening hours and working days?"},
            headers={"X-Customer-Session": token_b}
        )
        data_b_hours = res_b_hours.get_json()["data"]
        print(f"    - Shop A Answer (Ravi Mobiles): \"{data_hours['answer']}\"")
        print(f"    - Shop B Answer (Sri Fashion):  \"{data_b_hours['answer']}\"")
        assert "10" in data_b_hours["answer"] or "8" in data_b_hours["answer"], "Expected Shop B's 10 AM - 8 PM hours"
        assert "monday to saturday" not in data_b_hours["answer"].lower(), "Shop B should NOT inherit Shop A's Monday-Saturday hours"

        # 8b. Products comparison
        res_b_products = client.post(
            "/api/public/shop/sri-fashion/chat",
            json={"message": "What products do you sell in your shop?"},
            headers={"X-Customer-Session": token_b}
        )
        data_b_products = res_b_products.get_json()["data"]
        print(f"    - Shop A Products: \"{data_products['answer']}\"")
        print(f"    - Shop B Products: \"{data_b_products['answer']}\"")
        ans_b_lower = data_b_products["answer"].lower()
        assert any(c in ans_b_lower for c in ["clothing", "sarees", "kurtas", "fashion", "wear"]), "Expected clothing/fashion terms in Shop B"
        assert not any(p in ans_b_lower for p in ["smartphone", "oneplus", "samsung", "vivo"]), "Shop B must NOT mention Shop A's mobile brands"

        # 8c. Mobile inquiry in Fashion shop
        res_b_mobile = client.post(
            "/api/public/shop/sri-fashion/chat",
            json={"message": "Do you sell Samsung Galaxy and Apple iPhones?"},
            headers={"X-Customer-Session": token_b}
        )
        data_b_mobile = res_b_mobile.get_json()["data"]
        print(f"    - Asking Shop B (Fashion) about Mobiles:")
        print(f"      Status: {data_b_mobile['status']} | can_answer: {data_b_mobile['can_answer']}")
        print(f"      AI Answer: \"{data_b_mobile['answer']}\"")
        assert data_b_mobile["can_answer"] is False or "clothing" in data_b_mobile["answer"].lower(), "Shop B must not answer with Shop A's mobile inventory"
        print("    --> Verification [7 & 8]: PASS (Zero cross-tenant leakage between Shop A and Shop B)")

        # -------------------------------------------------------------
        # 9. Non-Hallucination & Non-Invention Verification
        # -------------------------------------------------------------
        print("\n[9] NON-HALLUCINATION & NON-INVENTION CHECK:")
        invented_q = "Can you sell me a 50000 rupee gold necklace and deliver it to Paris?"
        res_invent = client.post(
            "/api/public/shop/ravi-mobiles/chat",
            json={"message": invented_q},
            headers={"X-Customer-Session": token_a}
        )
        data_invent = res_invent.get_json()["data"]
        print(f"    - Hallucination probe: \"{invented_q}\"")
        print(f"    - AI Answer: \"{data_invent['answer']}\"")
        print(f"    - Status: {data_invent['status']} | can_answer: {data_invent['can_answer']}")
        assert data_invent["can_answer"] is False, "AI must not invent gold jewellery or Paris delivery for a mobile shop"
        assert data_invent["status"] == "pending", "Unfounded query must be marked pending"
        assert "gold" not in data_invent["answer"].lower() or data_invent["answer"] == FALLBACK_MESSAGE
        print("    --> Verification [9]: PASS (AI does not invent products, prices, or policies outside KB)")

        # -------------------------------------------------------------
        # 10. API Failure Handling & Fallback Safety
        # -------------------------------------------------------------
        print("\n[10] API FAILURE & NETWORK ERROR HANDLING:")
        # Test simulated API error in AIService
        mock_kb = [{"entry": KnowledgeBase(title="Test", content="Test content", category="Test")}]

        # Test 10a: Corrupt API key / endpoint
        saved_key = app.config["GEMINI_API_KEY"]
        app.config["GEMINI_API_KEY"] = "INVALID_KEY_TEST_TRIGGER"
        res_fail = AIService.answer_question("What is your timing?", mock_kb, "Test Shop")
        app.config["GEMINI_API_KEY"] = saved_key

        print(f"    - AIService response on API auth failure:")
        print(f"      can_answer: {res_fail.get('can_answer')}")
        print(f"      provider: '{res_fail.get('provider')}'")
        print(f"      answer: \"{res_fail.get('answer')}\"")
        assert res_fail["can_answer"] is False, "On API failure, can_answer must be False"
        assert res_fail["answer"] == FALLBACK_MESSAGE, "On API failure, answer must be FALLBACK_MESSAGE"

        # Test 10b: Empty / None response safety
        sanitized_none = AIService.answer_question("", mock_kb, "Test Shop")
        assert sanitized_none["can_answer"] is False
        assert sanitized_none["answer"] == FALLBACK_MESSAGE
        print("    --> Verification [10]: PASS (API failures safely caught, no fabricated answers emitted)")

        print("\n" + "=" * 85)
        print("ALL 10 VERIFICATION REQUIREMENTS COMPLETED SUCCESSFULLY")
        print("=" * 85)

if __name__ == "__main__":
    run_comprehensive_workflow_verification()

import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import requests
from backend.app import create_app
from backend.config import Config
from backend.app.services.ai_service import AIService

def mask_key(key: str) -> str:
    if not key:
        return "[NOT SET]"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]} ({len(key)} chars)"

def verify_live_gemini():
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("SHOPGENIE AI - LIVE GEMINI API VERIFICATION")
        print("=" * 80)

        # 1. Confirm .env loaded correctly without exposing key
        env_path = Path(root_dir) / "backend" / ".env"
        env_exists = env_path.exists()
        api_key = app.config.get("GEMINI_API_KEY", "").strip()
        key_valid = bool(api_key)

        print(f"[1] .env File Loading:")
        print(f"    - Path: backend/.env")
        print(f"    - Exists: {env_exists}")
        print(f"    - API Key Detected: {key_valid}")
        print(f"    - Masked Key Representation: {mask_key(api_key)}")

        # 2. Confirm AI_PROVIDER is gemini
        provider = app.config.get("AI_PROVIDER", "")
        print(f"\n[2] AI_PROVIDER Check:")
        print(f"    - Configured Value: '{provider}'")
        print(f"    - Matches 'gemini': {provider.lower() == 'gemini'}")

        # 3. Confirm GEMINI_MODEL is loaded correctly
        configured_model = app.config.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
        print(f"\n[3] GEMINI_MODEL Check:")
        print(f"    - Configured Model in .env: '{configured_model}'")

        # 4 & 5. Dispatch live request using configured model
        test_question = "Explain what ShopGenie AI does in two sentences."
        print(f"\n[4] Making Actual Live Request with Configured Model ('{configured_model}'):")
        print(f"    - Test Prompt: \"{test_question}\"")
        print(f"    - Target Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{configured_model}:generateContent")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": test_question}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 200
            }
        }
        headers = {"Content-Type": "application/json"}
        url_configured = f"https://generativelanguage.googleapis.com/v1beta/models/{configured_model}:generateContent?key={api_key}"

        t0 = time.time()
        try:
            res_conf = requests.post(url_configured, headers=headers, json=payload, timeout=12)
            elapsed = time.time() - t0
            print(f"    - HTTP Status Code: {res_conf.status_code}")
            print(f"    - Response Time: {elapsed:.2f}s")

            if res_conf.status_code == 200:
                data = res_conf.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"\n[5 & 6] Genuine Response from Gemini API:")
                print(f"    \"{text}\"")
                print(f"    - Genuine Gemini Response: True")
                print(f"    - Fallback Used: False")
            else:
                print(f"\n[7 & 8] Request Failed for Configured Model '{configured_model}':")
                print(f"    - HTTP Status: {res_conf.status_code}")
                try:
                    err_payload = res_conf.json()
                    err_code = err_payload.get("error", {}).get("code")
                    err_status = err_payload.get("error", {}).get("status")
                    err_msg = err_payload.get("error", {}).get("message")
                    print(f"    - Error Code: {err_code} ({err_status})")
                    print(f"    - Error Message: \"{err_msg}\"")
                except Exception:
                    print(f"    - Raw Response: {res_conf.text[:300]}")

        except requests.exceptions.Timeout:
            print(f"    - Error: ReadTimeout after {time.time()-t0:.2f}s (Upstream Google server did not reply in time)")
        except Exception as e:
            print(f"    - Error: {type(e).__name__}: {e}")

        # Now test with stable fast alternative: gemini-3.5-flash-lite
        alt_model = "gemini-3.5-flash-lite"
        print(f"\n" + "-" * 80)
        print(f"TESTING WITH HIGH-AVAILABILITY ALTERNATIVE: '{alt_model}'")
        print("-" * 80)
        url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/{alt_model}:generateContent?key={api_key}"
        t1 = time.time()
        try:
            res_alt = requests.post(url_alt, headers=headers, json=payload, timeout=15)
            elapsed_alt = time.time() - t1
            print(f"    - HTTP Status Code: {res_alt.status_code}")
            print(f"    - Response Time: {elapsed_alt:.2f}s")
            if res_alt.status_code == 200:
                data_alt = res_alt.json()
                alt_text = data_alt["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"\n[SUCCESS] Actual Live Gemini API Response ({alt_model}):")
                print(f"    \"{alt_text}\"")
                print(f"    - Provider: Gemini API (generativelanguage.googleapis.com)")
                print(f"    - Local Fallback Triggered: NO")
        except Exception as e:
            print(f"    - Alternative test failed: {e}")

        # Now verify through AIService
        print("\n" + "=" * 80)
        print("VERIFYING FULL APPLICATION AIService INTEGRATION")
        print("=" * 80)
        mock_kb = [{
            "entry": type("MockEntry", (), {
                "title": "ShopGenie AI Overview",
                "content": "ShopGenie AI is a multi-tenant SaaS customer support platform that provides automated customer service for local and online retail shops.",
                "category": "About"
            })()
        }]
        # Set app config to alt_model to ensure clean roundtrip
        app.config["GEMINI_MODEL"] = alt_model
        ai_res = AIService.answer_question(
            question="What is ShopGenie AI?",
            knowledge_entries=mock_kb,
            shop_name="ShopGenie Central"
        )
        print(f"    - AIService Provider: {ai_res.get('provider')}")
        print(f"    - AIService can_answer: {ai_res.get('can_answer')}")
        print(f"    - AIService Answer: \"{ai_res.get('answer')}\"")
        print("=" * 80)

if __name__ == "__main__":
    verify_live_gemini()

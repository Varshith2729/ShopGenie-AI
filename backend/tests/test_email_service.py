import pytest
import smtplib
from unittest.mock import patch, MagicMock
from backend.app.models import db, CustomerQuestion, EmailNotificationLog, Shop, User, Customer
from backend.app.services.email_service import EmailService

# ----------------------------------------------------------------------
# 1. Successful owner reply and email submission.
# ----------------------------------------------------------------------
def test_scenario_01_successful_owner_reply_and_email(client, auth_headers, monkeypatch, app):
    # Set email provider to resend with dummy key
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test_dummy_key_123")
    monkeypatch.setitem(app.config, "MAIL_FROM", "onboarding@resend.dev")

    # Customer creates session & asks question
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Alice", "last_name": "Wonder", "email": "alice@example.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you deliver on Sundays?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # Mock requests.post to simulate successful Resend response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "resend_msg_abc123"}

    with patch("backend.app.services.email_service.requests.post", return_value=mock_resp) as mock_post:
        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, we deliver on Sundays between 10 AM and 4 PM."
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["email_status"] == "sent"
        assert data["question"]["owner_answer"] == "Yes, we deliver on Sundays between 10 AM and 4 PM."
        assert "submitted successfully" in res.get_json()["message"]
        assert mock_post.called

# ----------------------------------------------------------------------
# 2. Correct customer email address used.
# ----------------------------------------------------------------------
def test_scenario_02_correct_customer_email_address(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_valid_key")

    target_email = "target.customer@domain.com"
    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Jane", "last_name": "Target", "email": target_email
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Is parking available?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "resend_msg_999"}

    with patch("backend.app.services.email_service.requests.post", return_value=mock_resp) as mock_post:
        client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, complimentary parking is available behind the store."
        }, headers=auth_headers)

        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["to"] == [target_email]

# ----------------------------------------------------------------------
# 3. Correct shop name and owner response in email.
# ----------------------------------------------------------------------
def test_scenario_03_correct_shop_name_and_owner_response(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_valid_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Robert", "last_name": "Pattinson", "email": "robert@example.com"
    }).get_json()["data"]["session_token"]

    question_text = "What is your holiday schedule?"
    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": question_text
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    owner_response = "We are open on all public holidays except New Year's Day."

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "resend_123"}

    with patch("backend.app.services.email_service.requests.post", return_value=mock_resp) as mock_post:
        client.post(f"/api/questions/{q_id}/answer", json={
            "answer": owner_response
        }, headers=auth_headers)

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        # Subject must be: Your Question Has Been Answered – Test Shop
        assert "Your Question Has Been Answered – Test Shop" in payload["subject"]
        assert "Test Shop" in payload["from"]
        assert owner_response in payload["text"]
        assert question_text in payload["text"]
        assert "Hello Robert Pattinson" in payload["text"]
        assert owner_response in payload["html"]

# ----------------------------------------------------------------------
# 4. Invalid Resend API key.
# ----------------------------------------------------------------------
def test_scenario_04_invalid_resend_api_key(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_invalid_expired_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Tom", "last_name": "Hardy", "email": "tom@example.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Can I pick up in store?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"message": "API key is invalid", "name": "authentication_error"}
    mock_resp.text = '{"message": "API key is invalid"}'

    with patch("backend.app.services.email_service.requests.post", return_value=mock_resp):
        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, in-store pickup is ready within 2 hours."
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        # Owner answer must be saved
        assert data["question"]["owner_answer"] == "Yes, in-store pickup is ready within 2 hours."
        assert data["email_status"] == "failed"
        assert "API key is invalid" in data["email_error"]
        assert "could not be sent" in res.get_json()["message"]

# ----------------------------------------------------------------------
# 5. SMTP authentication failure.
# ----------------------------------------------------------------------
def test_scenario_05_smtp_authentication_failure(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setitem(app.config, "SMTP_SERVER", "smtp.gmail.com")
    monkeypatch.setitem(app.config, "SMTP_PORT", 587)
    monkeypatch.setitem(app.config, "SMTP_USERNAME", "testuser@gmail.com")
    monkeypatch.setitem(app.config, "SMTP_PASSWORD", "wrongpassword")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Clark", "last_name": "Kent", "email": "clark@dailyplanet.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you offer corporate discounts?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # Mock smtplib to raise SMTPAuthenticationError
    with patch("backend.app.services.email_service.smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, 15% discount for corporate accounts."
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["email_status"] == "failed"
        assert "SMTP authentication failed" in data["email_error"]

# ----------------------------------------------------------------------
# 6. Missing / Invalid customer email.
# ----------------------------------------------------------------------
def test_scenario_06_missing_customer_email(client, auth_headers, app):
    with app.app_context():
        # Create a question with a customer who has an invalid email
        shop = Shop.query.first()
        cust = Customer(shop_id=shop.id, first_name="NoEmail", last_name="User", email="invalid-email-address")
        db.session.add(cust)
        db.session.flush()

        q = CustomerQuestion(
            shop_id=shop.id,
            customer_id=cust.id,
            question="Where is my order?",
            status="pending"
        )
        db.session.add(q)
        db.session.commit()
        q_id = q.id

    res = client.post(f"/api/questions/{q_id}/answer", json={
        "answer": "Your order is in transit."
    }, headers=auth_headers)

    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["email_status"] == "failed"
    assert "Invalid or missing customer email" in data["email_error"]

# ----------------------------------------------------------------------
# 7. Email provider unavailable (connection timeout).
# ----------------------------------------------------------------------
def test_scenario_07_email_provider_unavailable(client, auth_headers, monkeypatch, app):
    import requests
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Bruce", "last_name": "Wayne", "email": "bruce@wayne.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you sell night vision gear?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # Mock timeout
    with patch("backend.app.services.email_service.requests.post", side_effect=requests.Timeout("Connection timed out")):
        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, tactical gear is in our specialty catalog."
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["email_status"] == "failed"
        assert "timed out" in data["email_error"]

# ----------------------------------------------------------------------
# 8. Owner reply saved even when email fails.
# ----------------------------------------------------------------------
def test_scenario_08_owner_reply_saved_even_when_email_fails(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Barry", "last_name": "Allen", "email": "barry@centralcity.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "How fast is express shipping?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    answer_content = "Express shipping delivers within 24 hours guaranteed."

    # Simulate network failure
    with patch("backend.app.services.email_service.requests.post", side_effect=Exception("Network down")):
        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": answer_content
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["email_status"] == "failed"
        assert data["question"]["owner_answer"] == answer_content
        assert data["question"]["status"] == "answered"

        # Verify in database directly
        with app.app_context():
            saved_q = db.session.get(CustomerQuestion, q_id)
            assert saved_q.owner_answer == answer_content
            assert saved_q.status == "answered"

# ----------------------------------------------------------------------
# 9. Unauthorized owner cannot reply to another shop's question.
# ----------------------------------------------------------------------
def test_scenario_09_unauthorized_owner_cannot_reply_other_shop(client):
    # Register Owner 1 (Shop 1)
    res1 = client.post("/api/auth/register", json={
        "full_name": "Owner One", "email": "owner1@test.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Shop One", "slug": "shop-one"
    })
    token1 = res1.get_json()["data"]["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Register Owner 2 (Shop 2)
    res2 = client.post("/api/auth/register", json={
        "full_name": "Owner Two", "email": "owner2@test.com", "password": "password123",
        "confirm_password": "password123", "shop_name": "Shop Two", "slug": "shop-two"
    })
    token2 = res2.get_json()["data"]["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Customer asks question to Shop 1
    sess1 = client.post("/api/public/shop/shop-one/session", json={
        "first_name": "Cust", "last_name": "One", "email": "cust1@test.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/shop-one/chat", json={
        "message": "Do you repair screens?"
    }, headers={"X-Customer-Session": sess1})
    q1_id = chat.get_json()["data"]["question_id"]

    # Owner 2 attempts to reply to Shop 1's question -> Must return 404 unauthorized!
    hack_attempt = client.post(f"/api/questions/{q1_id}/answer", json={
        "answer": "Hijacked answer"
    }, headers=headers2)

    assert hack_attempt.status_code == 404
    assert "not found or unauthorized" in hack_attempt.get_json()["message"]

# ----------------------------------------------------------------------
# 10. Retry after email failure.
# ----------------------------------------------------------------------
def test_scenario_10_retry_after_email_failure(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Arthur", "last_name": "Curry", "email": "arthur@atlantis.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you ship internationally?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    # 1st attempt: fails
    mock_fail = MagicMock()
    mock_fail.status_code = 500
    mock_fail.json.return_value = {"message": "Internal Resend Error"}
    mock_fail.text = "Internal Resend Error"

    with patch("backend.app.services.email_service.requests.post", return_value=mock_fail):
        res1 = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, international maritime shipping is available."
        }, headers=auth_headers)
        assert res1.get_json()["data"]["email_status"] == "failed"

    # 2nd attempt: owner clicks Retry Email, this time succeeds
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = {"id": "resend_retry_success_456"}

    with patch("backend.app.services.email_service.requests.post", return_value=mock_ok):
        retry_res = client.post(f"/api/questions/{q_id}/retry-email", headers=auth_headers)
        assert retry_res.status_code == 200
        data = retry_res.get_json()["data"]
        assert data["email_status"] == "sent"
        assert data["email_retries"] >= 2

# ----------------------------------------------------------------------
# 11. Duplicate email prevention.
# ----------------------------------------------------------------------
def test_scenario_11_duplicate_email_prevention(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test_key")

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Victor", "last_name": "Stone", "email": "victor@star-labs.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you have cybernetic components?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = {"id": "resend_dup_test_1"}

    # 1st answer -> email sent successfully
    with patch("backend.app.services.email_service.requests.post", return_value=mock_ok) as mock_post:
        res1 = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Components are available on backorder."
        }, headers=auth_headers)
        assert res1.get_json()["data"]["email_status"] == "sent"
        assert mock_post.call_count == 1

    # 2nd answer submission (without force) -> Should NOT send duplicate email!
    with patch("backend.app.services.email_service.requests.post", return_value=mock_ok) as mock_post2:
        res2 = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Updated components notice."
        }, headers=auth_headers)
        assert res2.status_code == 200
        # Post was NOT called again
        assert mock_post2.call_count == 0
        assert "previously sent" in res2.get_json()["message"]

    # Also retry-email without force should reject with 400
    retry_res = client.post(f"/api/questions/{q_id}/retry-email", headers=auth_headers)
    assert retry_res.status_code == 400
    assert "already been successfully accepted" in retry_res.get_json()["message"]

# ----------------------------------------------------------------------
# 12. Successful SMTP handshake, STARTTLS and delivery.
# ----------------------------------------------------------------------
def test_scenario_12_successful_smtp_delivery(client, auth_headers, monkeypatch, app):
    monkeypatch.setitem(app.config, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setitem(app.config, "SMTP_SERVER", "smtp.gmail.com")
    monkeypatch.setitem(app.config, "SMTP_PORT", 587)
    monkeypatch.setitem(app.config, "SMTP_USERNAME", "shopowner@gmail.com")
    monkeypatch.setitem(app.config, "SMTP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setitem(app.config, "SMTP_USE_TLS", True)

    sess = client.post("/api/public/shop/test-shop/session", json={
        "first_name": "Diana", "last_name": "Prince", "email": "diana@themyscira.com"
    }).get_json()["data"]["session_token"]

    chat = client.post("/api/public/shop/test-shop/chat", json={
        "message": "Do you sell golden lassos?"
    }, headers={"X-Customer-Session": sess})
    q_id = chat.get_json()["data"]["question_id"]

    with patch("backend.app.services.email_service.smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        res = client.post(f"/api/questions/{q_id}/answer", json={
            "answer": "Yes, handcrafted Amazonian artifacts are in stock."
        }, headers=auth_headers)

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["email_status"] == "sent"
        assert data["question"]["owner_answer"] == "Yes, handcrafted Amazonian artifacts are in stock."

        # Verify SMTP sequence: ehlo -> starttls -> ehlo -> login -> send_message
        assert mock_server.ehlo.call_count >= 2
        assert mock_server.starttls.call_count == 1
        # Password spaces must be stripped
        mock_server.login.assert_called_once_with("shopowner@gmail.com", "abcdefghijklmnop")
        assert mock_server.send_message.call_count == 1
        sent_msg = mock_server.send_message.call_args[0][0]
        assert "diana@themyscira.com" in sent_msg["To"]
        assert "Test Shop" in sent_msg["From"]
        assert "Your Question Has Been Answered" in sent_msg["Subject"]

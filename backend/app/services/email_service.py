import re
import socket
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from flask import current_app

logger = logging.getLogger(__name__)

class EmailService:
    @classmethod
    def get_provider_name(cls) -> str:
        """Determine configured email provider."""
        provider = current_app.config.get("EMAIL_PROVIDER", "").lower().strip()
        if provider:
            return provider
            
        # Auto-detect from environment
        if current_app.config.get("RESEND_API_KEY"):
            return "resend"
        if current_app.config.get("SMTP_SERVER") and current_app.config.get("SMTP_USERNAME"):
            return "smtp"
            
        return "unconfigured"

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Validate recipient email address syntax."""
        if not email or not isinstance(email, str):
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    @classmethod
    def send_customer_answer_email(
        cls, 
        customer_name: str, 
        customer_email: str, 
        shop_name: str, 
        question: str, 
        answer: str,
        question_id: int = None,
        is_follow_up: bool = False
    ) -> dict:
        """
        Send answer notification email to customer. Supports conversation threading
        with Message-ID, In-Reply-To, References, and custom Reply-To for two-way communication.
        Returns:
            {
                "success": bool,
                "status": "sent" | "failed",
                "error": str | None,
                "provider": str,
                "provider_id": str | None
            }
        """
        # 1. Validate recipient email
        if not cls.is_valid_email(customer_email):
            err_msg = f"Invalid or missing customer email address: '{customer_email}'"
            logger.error(err_msg)
            return {
                "success": False,
                "status": "failed",
                "error": err_msg,
                "provider": "validation",
                "provider_id": None
            }

        cust_display_name = customer_name.strip() if customer_name and customer_name.strip() else "Valued Customer"
        safe_shop_name = shop_name.strip() if shop_name and shop_name.strip() else "ShopGenie Store"
        
        # 2. Email Subject (with thread reference if question_id is provided)
        ref_tag = f" [Ref: #SG-{question_id}]" if question_id else ""
        if is_follow_up:
            subject = f"New Response from {safe_shop_name}{ref_tag}"
        else:
            subject = f"Your Question Has Been Answered – {safe_shop_name}{ref_tag}"

        reply_instruction = (
            f"\n\n--- Please reply above this line to respond to {safe_shop_name}{ref_tag} ---\n"
            if question_id else ""
        )

        intro_greeting = (
            f"The owner of {safe_shop_name} has sent a follow-up response to your conversation."
            if is_follow_up else
            f"Good news! The owner of {safe_shop_name} has responded to your question."
        )

        # 3. Plain Text Body (as per specification with thread delimiter)
        plain_body = f"""Hello {cust_display_name},

{intro_greeting}

Your Question:
{question}

Owner's Response:
{answer}

Thank you for contacting {safe_shop_name}.{reply_instruction}

Best regards,
ShopGenie AI Customer Support
"""

        # 4. Professional HTML Email Template
        reply_banner_html = f"""
        <div style="margin-top: 20px; padding: 12px; background: #eff6ff; border: 1px dashed #93c5fd; border-radius: 8px; text-align: center; font-size: 12px; color: #1e40af;">
          <strong>Two-Way Reply:</strong> You can reply directly to this email from your email inbox to send a follow-up message to the shop owner.{ref_tag}
        </div>
        """ if question_id else ""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background-color: #f8fafc;
      margin: 0;
      padding: 24px 12px;
    }}
    .email-wrapper {{
      max-width: 600px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .email-header {{
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      padding: 28px 24px;
      text-align: center;
    }}
    .email-header h1 {{
      margin: 0;
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}
    .email-header p {{
      margin: 6px 0 0 0;
      font-size: 13px;
      color: #dbeafe;
    }}
    .email-content {{
      padding: 28px 24px;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 12px;
    }}
    .intro-text {{
      font-size: 14px;
      color: #475569;
      margin-bottom: 20px;
    }}
    .qa-card {{
      background: #f8fafc;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      padding: 16px;
      margin-bottom: 20px;
    }}
    .qa-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #64748b;
      margin-bottom: 4px;
    }}
    .qa-question {{
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      margin: 0 0 16px 0;
      background: #ffffff;
      padding: 12px;
      border-radius: 6px;
      border-left: 3px solid #64748b;
    }}
    .qa-answer-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #2563eb;
      margin-bottom: 4px;
    }}
    .qa-answer {{
      font-size: 14px;
      font-weight: 500;
      color: #0f172a;
      margin: 0;
      background: #ffffff;
      padding: 12px;
      border-radius: 6px;
      border-left: 3px solid #2563eb;
    }}
    .outro-text {{
      font-size: 13px;
      color: #475569;
      margin-top: 20px;
    }}
    .signoff {{
      font-size: 13px;
      color: #334155;
      margin-top: 16px;
    }}
    .signoff strong {{
      color: #0f172a;
    }}
    .email-footer {{
      background: #f1f5f9;
      border-top: 1px solid #e2e8f0;
      padding: 16px 24px;
      text-align: center;
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="email-wrapper">
    <div class="email-header">
      <h1>{safe_shop_name}</h1>
      <p>Customer Support Notification</p>
    </div>
    <div class="email-content">
      <div class="greeting">Hello {cust_display_name},</div>
      <p class="intro-text">{intro_greeting}</p>
      
      <div class="qa-card">
        <div class="qa-label">Your Question:</div>
        <p class="qa-question">{question}</p>
        
        <div class="qa-answer-label">Owner's Response:</div>
        <p class="qa-answer">{answer}</p>
      </div>

      {reply_banner_html}

      <p class="outro-text">Thank you for contacting {safe_shop_name}.</p>
      <div class="signoff">
        Best regards,<br>
        <strong>ShopGenie AI Customer Support</strong>
      </div>
    </div>
    <div class="email-footer">
      Powered by ShopGenie AI &bull; Intelligent Multi-Tenant Customer Care
    </div>
  </div>
</body>
</html>
"""

        provider = cls.get_provider_name()
        
        # -------------------------------------------------------------
        # A. Mock Mode for Tests
        # -------------------------------------------------------------
        if provider == "mock":
            logger.info(f"[TEST MOCK EMAIL] Mock dispatch accepted to {customer_email} for shop '{safe_shop_name}'")
            return {
                "success": True,
                "status": "sent",
                "error": None,
                "provider": "mock",
                "provider_id": "mock_email_123"
            }

        # -------------------------------------------------------------
        # B. Resend Provider
        # -------------------------------------------------------------
        if provider == "resend":
            resend_key = current_app.config.get("RESEND_API_KEY", "").strip()
            if not resend_key:
                err_msg = "Resend API key is missing. Set RESEND_API_KEY in your .env configuration."
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "resend",
                    "provider_id": None
                }
                
            raw_from = current_app.config.get("MAIL_FROM", "onboarding@resend.dev").strip()
            # Clean shop name of commas/quotes to ensure valid RFC 5322 address
            clean_display_name = re.sub(r'[\r\n",]', '', safe_shop_name).strip()
            
            # Format from address
            if "<" in raw_from and ">" in raw_from:
                from_address = raw_from
            else:
                from_address = f"{clean_display_name} <{raw_from}>"

            logger.info(f"Attempting email dispatch via Resend to {customer_email} from {from_address}")
            
            resend_payload = {
                "from": from_address,
                "to": [customer_email.strip()],
                "subject": subject,
                "text": plain_body,
                "html": html_body
            }
            reply_to = current_app.config.get("INBOUND_REPLY_EMAIL", "").strip() or current_app.config.get("SMTP_USERNAME", "").strip()
            if reply_to:
                resend_payload["reply_to"] = reply_to
            if question_id:
                resend_payload["headers"] = {
                    "Message-ID": f"<shopgenie-q{question_id}-{int(datetime.now(timezone.utc).timestamp())}@shopgenie.local>",
                    "In-Reply-To": f"<shopgenie-q{question_id}@shopgenie.local>",
                    "References": f"<shopgenie-q{question_id}@shopgenie.local>"
                }

            try:
                res = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_key}",
                        "Content-Type": "application/json"
                    },
                    json=resend_payload,
                    timeout=12
                )
                
                if res.status_code in (200, 201):
                    res_data = res.json()
                    email_id = res_data.get("id")
                    logger.info(f"Email successfully accepted by Resend provider. ID: {email_id} for recipient: {customer_email}")
                    return {
                        "success": True,
                        "status": "sent",
                        "error": None,
                        "provider": "resend",
                        "provider_id": email_id
                    }
                else:
                    error_detail = "Unknown Resend error"
                    try:
                        err_json = res.json()
                        error_detail = err_json.get("message") or err_json.get("name") or res.text
                    except Exception:
                        error_detail = res.text
                    
                    err_msg = f"Resend API rejected request (HTTP {res.status_code}): {error_detail}"
                    logger.error(f"Resend delivery error for {customer_email}: {err_msg}")
                    return {
                        "success": False,
                        "status": "failed",
                        "error": err_msg,
                        "provider": "resend",
                        "provider_id": None
                    }
                    
            except requests.Timeout:
                err_msg = "Resend API connection timed out after 12 seconds."
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "resend",
                    "provider_id": None
                }
            except Exception as e:
                err_msg = f"Failed to connect to Resend API: {str(e)}"
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "resend",
                    "provider_id": None
                }

        # -------------------------------------------------------------
        # C. SMTP Provider (Gmail / Standard SMTP)
        # -------------------------------------------------------------
        if provider == "smtp":
            smtp_server = current_app.config.get("SMTP_SERVER", "").strip()
            raw_port = current_app.config.get("SMTP_PORT", 587)
            try:
                smtp_port = int(raw_port)
            except (ValueError, TypeError):
                smtp_port = 587

            smtp_user = current_app.config.get("SMTP_USERNAME", "").strip()
            # Clean password: strip whitespace often copied from Google 16-character App Passwords
            smtp_password = current_app.config.get("SMTP_PASSWORD", "").replace(" ", "").strip()
            use_tls = current_app.config.get("SMTP_USE_TLS", True)
            raw_timeout = current_app.config.get("SMTP_TIMEOUT", 10)
            try:
                timeout = float(raw_timeout)
            except (ValueError, TypeError):
                timeout = 10.0

            if not smtp_server or not smtp_user or not smtp_password:
                err_msg = "SMTP configuration incomplete. SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD are required in .env."
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }

            # Safely mask email address for diagnostics without exposing credentials
            masked_user = re.sub(r'(?<=.).(?=.*@)', '*', smtp_user) if "@" in smtp_user else "***"
            logger.info(f"Initiating SMTP dispatch ({smtp_server}:{smtp_port}) for recipient {customer_email} as '{masked_user}'")

            clean_display_name = re.sub(r'[\r\n",]', '', safe_shop_name).strip()
            from_address = f"{clean_display_name} <{smtp_user}>"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_address
            msg["To"] = customer_email.strip()

            # Threading and Reply-To headers for two-way email workflow
            reply_to = current_app.config.get("INBOUND_REPLY_EMAIL", "").strip() or smtp_user
            msg["Reply-To"] = reply_to
            if question_id:
                msg["Message-ID"] = f"<shopgenie-q{question_id}-{int(datetime.now(timezone.utc).timestamp())}@shopgenie.local>"
                msg["In-Reply-To"] = f"<shopgenie-q{question_id}@shopgenie.local>"
                msg["References"] = f"<shopgenie-q{question_id}@shopgenie.local>"

            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            try:
                logger.info(f"[SMTP Stage 1/5] Connecting to SMTP host {smtp_server}:{smtp_port} (timeout={timeout}s)...")
                with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as server:
                    logger.info("[SMTP Stage 2/5] Connection opened. Sending initial EHLO...")
                    server.ehlo()

                    if use_tls:
                        logger.info("[SMTP Stage 3/5] Initiating STARTTLS with default SSL context...")
                        ssl_context = ssl.create_default_context()
                        server.starttls(context=ssl_context)
                        logger.info("[SMTP Stage 3/5] STARTTLS succeeded. Re-negotiating EHLO over encrypted TLS channel...")
                        server.ehlo()
                    else:
                        logger.info("[SMTP Stage 3/5] STARTTLS bypassed (SMTP_USE_TLS=False)")

                    logger.info(f"[SMTP Stage 4/5] Authenticating as user '{masked_user}'...")
                    server.login(smtp_user, smtp_password)
                    logger.info("[SMTP Stage 4/5] SMTP authentication successful.")

                    logger.info(f"[SMTP Stage 5/5] Dispatching message using send_message to {customer_email}...")
                    server.send_message(msg)
                    logger.info(f"[SMTP Stage 5/5] Email successfully accepted by SMTP server for {customer_email}")

                return {
                    "success": True,
                    "status": "sent",
                    "error": None,
                    "provider": "smtp",
                    "provider_id": None
                }

            except smtplib.SMTPAuthenticationError as e:
                err_msg = f"SMTP authentication failed for user '{masked_user}'. Please verify your credentials or Gmail 16-character App Password."
                logger.error(f"{err_msg} Details: {str(e)}")
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }
            except smtplib.SMTPServerDisconnected as e:
                err_msg = f"SMTP delivery failed: Connection unexpectedly closed by {smtp_server}:{smtp_port} ({str(e)})."
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }
            except (socket.timeout, TimeoutError):
                err_msg = f"Connection to SMTP server '{smtp_server}:{smtp_port}' timed out after {timeout} seconds."
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }
            except (smtplib.SMTPConnectError, ConnectionRefusedError, socket.gaierror) as e:
                err_msg = f"Could not connect to SMTP server '{smtp_server}:{smtp_port}': {str(e)}"
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }
            except Exception as e:
                err_msg = f"SMTP delivery failed: {str(e)}"
                logger.error(err_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "error": err_msg,
                    "provider": "smtp",
                    "provider_id": None
                }

        # -------------------------------------------------------------
        # D. Unconfigured Provider
        # -------------------------------------------------------------
        err_msg = (
            "No email provider configured. Please configure RESEND_API_KEY (or SMTP credentials) in backend/.env"
        )
        logger.warning(err_msg)
        return {
            "success": False,
            "status": "failed",
            "error": err_msg,
            "provider": "none",
            "provider_id": None
        }

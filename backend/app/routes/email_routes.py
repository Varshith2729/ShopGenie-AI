import logging
from flask import Blueprint, request, g, current_app
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.services.email_inbound_service import EmailInboundService
from backend.app.services.email_sync_service import EmailSyncService
from backend.app.utils.helpers import success_response, error_response

logger = logging.getLogger(__name__)

email_bp = Blueprint("email_routes", __name__)

@email_bp.route("/inbound", methods=["POST"])
@email_bp.route("/webhooks/inbound-email", methods=["POST"])
def handle_inbound_webhook():
    """
    Inbound email webhook endpoint.
    Compatible with Resend Inbound webhooks, SendGrid, Postmark, and generic mail forwarders.
    Parses sender, subject, headers, and body, matching the email to the original question.
    """
    # 1. Optional Webhook Secret Authentication
    expected_secret = current_app.config.get("INBOUND_WEBHOOK_SECRET")
    if expected_secret:
        header_secret = request.headers.get("X-Webhook-Secret") or request.args.get("secret")
        if not header_secret or header_secret.strip() != expected_secret.strip():
            logger.warning("Inbound webhook authentication failed: invalid secret.")
            return error_response("Unauthorized webhook signature or secret.", 401)

    payload = request.get_json(silent=True) or {}
    if not payload and request.form:
        payload = request.form.to_dict()

    sender = payload.get("from") or payload.get("sender") or payload.get("from_email") or ""
    to = payload.get("to") or payload.get("recipient") or ""
    if isinstance(to, list) and to:
        to = to[0]

    subject = payload.get("subject", "")
    body_text = payload.get("text") or payload.get("body") or payload.get("content") or payload.get("html") or ""

    headers = payload.get("headers") or {}
    message_id = payload.get("message_id") or headers.get("message-id") or headers.get("Message-ID")
    in_reply_to = payload.get("in_reply_to") or headers.get("in-reply-to") or headers.get("In-Reply-To")
    references = payload.get("references") or headers.get("references") or headers.get("References")

    result = EmailInboundService.process_inbound_message(
        sender=str(sender),
        recipient=str(to),
        subject=str(subject),
        body_text=str(body_text),
        message_id=str(message_id) if message_id else None,
        in_reply_to=str(in_reply_to) if in_reply_to else None,
        references=str(references) if references else None
    )

    if result.get("success"):
        return success_response(result, "Inbound email processed successfully.", 200)
    else:
        status_code = result.get("status_code", 400)
        return error_response(result.get("error", "Failed to process inbound email."), status_code)

@email_bp.route("/sync", methods=["POST"])
@jwt_required
def sync_email_inbox():
    """
    On-demand Gmail IMAP synchronization endpoint for shop owners.
    Connects to the configured Gmail account, fetches new customer replies,
    and updates the shop's question conversation threads.
    """
    shop_id = g.current_shop.id
    logger.info(f"Shop #{shop_id} ('{g.current_shop.shop_name}') initiated Gmail sync...")

    sync_result = EmailSyncService.sync_gmail_inbox(shop_id=shop_id)

    if sync_result.get("success"):
        processed = sync_result.get("processed", 0)
        msg = f"Synced {processed} new customer replies from Gmail." if processed > 0 else "Inbox checked. No new customer replies found."
        return success_response(sync_result, msg, 200)
    else:
        return error_response(sync_result.get("error", "Gmail synchronization failed."), 502)


import email
from email.header import decode_header
import imaplib
import logging
from flask import current_app
from backend.app.services.email_inbound_service import EmailInboundService

logger = logging.getLogger(__name__)

def _decode_mime_header(header_value: str) -> str:
    """Decode RFC 2047 encoded email headers."""
    if not header_value:
        return ""
    decoded_fragments = []
    for fragment, encoding in decode_header(header_value):
        if isinstance(fragment, bytes):
            try:
                decoded_fragments.append(fragment.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(fragment.decode("utf-8", errors="replace"))
        else:
            decoded_fragments.append(str(fragment))
    return "".join(decoded_fragments)

class EmailSyncService:
    @classmethod
    def sync_gmail_inbox(cls, shop_id: int = None) -> dict:
        """
        Connect to Gmail via IMAP over SSL to fetch and process incoming customer replies.
        Reuses the existing verified Gmail credentials from backend/.env.
        """
        imap_server = current_app.config.get("IMAP_SERVER", "imap.gmail.com")
        username = current_app.config.get("SMTP_USERNAME", "").strip()
        password = current_app.config.get("SMTP_PASSWORD", "").replace(" ", "").strip()

        if not username or not password:
            return {
                "success": False,
                "error": "Gmail credentials (SMTP_USERNAME / SMTP_PASSWORD) are not configured in .env",
                "processed": 0
            }

        mail = None
        processed_count = 0
        synced_questions = []
        errors = []

        try:
            logger.info(f"Connecting to IMAP server {imap_server}:993 to check for customer replies...")
            mail = imaplib.IMAP4_SSL(imap_server, 993)
            mail.login(username, password)
            mail.select("INBOX")

            # Search for unseen messages or subject containing SG- reference
            status, search_data = mail.search(None, '(UNSEEN SUBJECT "SG-")')
            msg_ids = search_data[0].split() if status == "OK" and search_data and search_data[0] else []

            # Also check any UNSEEN message if none found with explicit subject
            if not msg_ids:
                status, search_data = mail.search(None, "UNSEEN")
                msg_ids = search_data[0].split() if status == "OK" and search_data and search_data[0] else []

            logger.info(f"Found {len(msg_ids)} potential incoming email messages in inbox.")

            for msg_id in msg_ids:
                try:
                    res, msg_data = mail.fetch(msg_id, "(RFC822)")
                    if res != "OK" or not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    from_header = _decode_mime_header(msg.get("From", ""))
                    to_header = _decode_mime_header(msg.get("To", ""))
                    subject_header = _decode_mime_header(msg.get("Subject", ""))
                    message_id_header = msg.get("Message-ID", "")
                    in_reply_to_header = msg.get("In-Reply-To", "")
                    references_header = msg.get("References", "")

                    # Extract plain text content
                    body_content = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    charset = part.get_content_charset() or "utf-8"
                                    body_content = payload.decode(charset, errors="replace")
                                    break
                        # Fallback to text/html if plain text was empty
                        if not body_content:
                            for part in msg.walk():
                                if part.get_content_type() == "text/html":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset() or "utf-8"
                                        body_content = payload.decode(charset, errors="replace")
                                        break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or "utf-8"
                            body_content = payload.decode(charset, errors="replace")

                    # Process through Inbound Service
                    result = EmailInboundService.process_inbound_message(
                        sender=from_header,
                        recipient=to_header,
                        subject=subject_header,
                        body_text=body_content,
                        message_id=message_id_header,
                        in_reply_to=in_reply_to_header,
                        references=references_header
                    )

                    if result.get("success"):
                        # Mark email as read in Gmail
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        if result.get("status") == "processed":
                            processed_count += 1
                            synced_questions.append(result.get("question_id"))
                    else:
                        errors.append(f"Msg #{msg_id.decode()}: {result.get('error')}")

                except Exception as inner_ex:
                    logger.error(f"Error processing email message #{msg_id}: {inner_ex}")
                    errors.append(str(inner_ex))

            return {
                "success": True,
                "processed": processed_count,
                "synced_questions": synced_questions,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"IMAP sync failed: {e}")
            return {
                "success": False,
                "error": f"IMAP connection failed: {str(e)}",
                "processed": 0
            }
        finally:
            if mail is not None:
                try:
                    mail.close()
                except Exception:
                    pass
                try:
                    mail.logout()
                except Exception:
                    pass


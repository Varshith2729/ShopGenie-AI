import re
import logging
from datetime import datetime, timezone
from backend.app.models import db, CustomerQuestion, Message, ActivityLog, Customer

logger = logging.getLogger(__name__)

class EmailInboundService:
    @staticmethod
    def extract_question_id(subject: str = "", body: str = "", in_reply_to: str = "", references: str = "", to_address: str = "") -> int:
        """
        Extract question_id using reference tags in Subject, In-Reply-To, References, Body, or To address.
        Supports standard ShopGenie formats like [Ref: #SG-123], #SG-123, SG-123, and shopgenie-q123.
        """
        sources = [
            subject or "",
            in_reply_to or "",
            references or "",
            to_address or "",
            body or ""
        ]
        
        patterns = [
            r'\[Ref:\s*#?SG-(\d+)\]',
            r'#SG-(\d+)',
            r'SG-(\d+)',
            r'shopgenie-q(\d+)',
            r'reply\+q(\d+)'
        ]
        
        for text in sources:
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    try:
                        return int(m.group(1))
                    except (ValueError, TypeError):
                        pass
        return None

    @staticmethod
    def clean_reply_body(raw_body: str) -> str:
        """
        Extract only the new reply text from the customer, stripping quoted threads and delimiters.
        """
        if not raw_body:
            return ""
            
        text = raw_body.strip()
        
        # 1. Delimiter lines
        delimiter_patterns = [
            r'---+\s*(?:Please\s+)?reply above this line.*$',
            r'On\s+.+?wrote:.*$',
            r'From:\s+.+?Sent:.*$',
            r'________________________________.*$',
            r'Begin forwarded message:.*$'
        ]
        
        for pat in delimiter_patterns:
            split_parts = re.split(pat, text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if len(split_parts) > 1 and split_parts[0].strip():
                text = split_parts[0].strip()
                break

        # 2. Strip quoted lines starting with '>'
        lines = [line for line in text.split("\n") if not line.strip().startswith(">")]
        cleaned = "\n".join(lines).strip()
        return cleaned or text.strip()

    @classmethod
    def process_inbound_message(
        cls,
        sender: str,
        recipient: str,
        subject: str,
        body_text: str,
        message_id: str = None,
        in_reply_to: str = None,
        references: str = None
    ) -> dict:
        """
        Process an inbound customer reply email.
        Enforces tenant isolation, security authentication, and deduplication.
        """
        if not sender:
            return {"success": False, "error": "Missing sender email address", "status_code": 400}

        # Normalize sender
        sender_clean = sender.lower().strip()
        if "<" in sender_clean and ">" in sender_clean:
            match = re.search(r'<([^>]+)>', sender_clean)
            if match:
                sender_clean = match.group(1).strip()

        # 1. Identify question_id
        question_id = cls.extract_question_id(
            subject=subject,
            body=body_text,
            in_reply_to=in_reply_to,
            references=references,
            to_address=recipient
        )

        if not question_id:
            logger.warning(f"Inbound email from '{sender_clean}' rejected: No question reference found in subject, headers, or body.")
            return {
                "success": False,
                "error": "No question reference found in message (e.g. [Ref: #SG-123])",
                "status_code": 422
            }

        # 2. Retrieve question record
        question = db.session.get(CustomerQuestion, question_id)
        if not question:
            logger.warning(f"Inbound email referenced non-existent Question #{question_id}.")
            return {
                "success": False,
                "error": f"Question #{question_id} not found",
                "status_code": 404
            }

        # 3. Security: Tenant Isolation & Sender Authentication
        customer = question.customer
        if not customer:
            return {"success": False, "error": "Associated customer record not found", "status_code": 404}

        cust_email = customer.email.lower().strip()
        if sender_clean != cust_email:
            logger.warning(
                f"Unauthorized inbound email sender '{sender_clean}' attempted to update Question #{question_id} "
                f"(expected '{cust_email}'). Rejecting for tenant security."
            )
            return {
                "success": False,
                "error": f"Sender '{sender_clean}' is not authorized to reply to this conversation.",
                "status_code": 403
            }

        # 4. Deduplication by Message-ID
        if message_id:
            existing_msg = Message.query.filter_by(
                shop_id=question.shop_id,
                email_message_id=message_id
            ).first()
            if existing_msg:
                logger.info(f"Duplicate email Message-ID '{message_id}' already processed. Skipping.")
                return {
                    "success": True,
                    "status": "duplicate",
                    "message": "Message already processed",
                    "question_id": question.id,
                    "message_id": existing_msg.id
                }

        cleaned_text = cls.clean_reply_body(body_text)
        if not cleaned_text:
            cleaned_text = body_text.strip() or "Received customer response via email."

        # Check for duplicate text within last 60 seconds
        if question.conversation_id:
            recent_duplicate = Message.query.filter_by(
                conversation_id=question.conversation_id,
                sender_type="customer",
                message_content=cleaned_text
            ).first()
            if recent_duplicate and recent_duplicate.created_at:
                now_utc = datetime.now(timezone.utc)
                msg_time = recent_duplicate.created_at
                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=timezone.utc)
                if (now_utc - msg_time).total_seconds() < 60:
                    logger.info(f"Duplicate message content received within 60s for Question #{question.id}. Skipping.")
                    return {
                        "success": True,
                        "status": "duplicate",
                        "message": "Duplicate message content detected within 60s",
                        "question_id": question.id,
                        "message_id": recent_duplicate.id
                    }

        # 5. Persist message to conversation
        try:
            new_msg = Message(
                shop_id=question.shop_id,
                conversation_id=question.conversation_id,
                sender_type="customer",
                message_content=cleaned_text,
                email_message_id=message_id
            )
            db.session.add(new_msg)

            # Update question status to 'customer_replied' so the shop owner is alerted
            question.status = "customer_replied"
            
            # Log activity
            activity = ActivityLog(
                shop_id=question.shop_id,
                user_id=None,
                action="customer_email_reply",
                details=f"Customer {customer.email} replied to Question #{question.id} via email: '{cleaned_text[:60]}...'"
            )
            db.session.add(activity)
            db.session.commit()

            logger.info(f"Successfully processed customer email reply for Question #{question.id} (Shop #{question.shop_id}).")
            return {
                "success": True,
                "status": "processed",
                "question_id": question.id,
                "shop_id": question.shop_id,
                "message_id": new_msg.id,
                "customer_email": cust_email,
                "reply_content": cleaned_text
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error persisting inbound email for Question #{question_id}: {e}")
            return {"success": False, "error": f"Database error: {str(e)}", "status_code": 500}


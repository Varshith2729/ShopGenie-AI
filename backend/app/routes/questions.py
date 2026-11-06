from datetime import datetime, timezone
import logging
from flask import Blueprint, request, g
from backend.app.models import db, CustomerQuestion, KnowledgeBase, ActivityLog, EmailNotificationLog, Message
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response, error_response
from backend.app.services.email_service import EmailService

logger = logging.getLogger(__name__)

questions_bp = Blueprint("questions", __name__)

@questions_bp.route("", methods=["GET"])
@jwt_required
def list_questions():
    shop_id = g.current_shop.id
    status_filter = request.args.get("status", "").strip().lower()
    
    query = CustomerQuestion.query.filter_by(shop_id=shop_id)
    if status_filter in ("pending", "answered"):
        query = query.filter_by(status=status_filter)
        
    questions = query.order_by(CustomerQuestion.created_at.desc()).all()
    
    return success_response({
        "questions": [q.to_dict() for q in questions],
        "total": len(questions)
    })

@questions_bp.route("/<int:question_id>", methods=["GET"])
@jwt_required
def get_question(question_id):
    shop_id = g.current_shop.id
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)
        
    data = question.to_dict()
    data["notification_logs"] = [log.to_dict() for log in question.notification_logs] if question.notification_logs else []
    return success_response(data)

@questions_bp.route("/<int:question_id>/answer", methods=["POST"])
@jwt_required
def answer_question(question_id):
    shop_id = g.current_shop.id
    # Strict tenant isolation
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)
        
    data = request.get_json() or {}
    owner_answer = data.get("answer", "").strip()
    force_resend = bool(data.get("force_resend", False))
    
    if not owner_answer:
        return error_response("Answer cannot be empty.", 400)

    customer = question.customer
    if not customer:
        return error_response("Associated customer record not found.", 404)

    # 1. Save owner response in database FIRST
    try:
        is_already_sent = (question.email_status == "sent")
        question.owner_answer = owner_answer
        question.status = "answered"
        question.answered_at = datetime.now(timezone.utc)

        # 2. Add or update Knowledge Base entry
        kb_title = f"FAQ: {question.question[:70]}"
        kb_content = f"Question: {question.question}\nAnswer: {owner_answer}"
        
        # Check if KB entry already exists for this question
        existing_kb = KnowledgeBase.query.filter_by(
            shop_id=shop_id, 
            source_type="pending_answered",
            title=kb_title
        ).first()

        if existing_kb:
            existing_kb.content = kb_content
            kb_entry = existing_kb
        else:
            kb_entry = KnowledgeBase(
                shop_id=shop_id,
                title=kb_title,
                content=kb_content,
                category="Customer FAQ",
                source_type="pending_answered"
            )
            db.session.add(kb_entry)

        # 3. Append to conversation thread if active
        if question.conversation_id:
            owner_msg = Message(
                shop_id=shop_id,
                conversation_id=question.conversation_id,
                sender_type="owner",
                message_content=owner_answer
            )
            db.session.add(owner_msg)

        # 4. Activity Log
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="question_answered",
            details=f"Answered customer question #{question.id} for {customer.email}"
        )
        db.session.add(log)
        
        # Commit response data immediately before attempting email
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to save owner response: {e}")
        return error_response(f"Database error saving response: {str(e)}", 500)

    # 4. Duplicate Email Prevention
    if is_already_sent and not force_resend:
        logger.info(f"Question #{question.id} email notification already sent previously. Skipping duplicate send.")
        return success_response({
            "question": question.to_dict(),
            "knowledge_entry": kb_entry.to_dict(),
            "email_status": "sent",
            "email_error": None,
            "message": "Answer updated. Email notification was already sent previously to this customer."
        }, "Your reply has been saved and the email notification was previously sent.")

    # 5. Dispatch email notification to customer
    email_res = EmailService.send_customer_answer_email(
        customer_name=f"{customer.first_name} {customer.last_name}",
        customer_email=customer.email,
        shop_name=g.current_shop.shop_name,
        question=question.question,
        answer=owner_answer,
        question_id=question.id
    )

    # 6. Record delivery status and audit log
    try:
        provider_name = email_res.get("provider", "unknown")
        
        if email_res.get("success"):
            question.email_status = "sent"
            question.email_error = None
            question.email_sent_at = datetime.now(timezone.utc)
            question.email_provider = provider_name
        else:
            question.email_status = "failed"
            question.email_error = email_res.get("error")
            question.email_provider = provider_name

        question.email_retries = (question.email_retries or 0) + 1

        # Notification Audit Log
        notif_log = EmailNotificationLog(
            shop_id=shop_id,
            customer_question_id=question.id,
            recipient_email=customer.email,
            provider=provider_name,
            status=question.email_status,
            error_message=email_res.get("error")
        )
        db.session.add(notif_log)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to record email status: {e}")

    # 7. Build user-facing response message matching Section 9
    if question.email_status == "sent":
        user_message = "Your reply has been saved and the email notification has been submitted successfully."
    else:
        user_message = f"Your reply has been saved, but the email notification could not be sent. Please retry. (Error: {email_res.get('error')})"

    return success_response({
        "question": question.to_dict(),
        "knowledge_entry": kb_entry.to_dict(),
        "email_status": question.email_status,
        "email_error": question.email_error,
        "email_retries": question.email_retries,
        "email_provider": question.email_provider
    }, user_message)

@questions_bp.route("/<int:question_id>/retry-email", methods=["POST"])
@jwt_required
def retry_email(question_id):
    shop_id = g.current_shop.id
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)
        
    if not question.owner_answer:
        return error_response("Cannot send email: Question has not been answered yet.", 400)

    customer = question.customer
    if not customer:
        return error_response("Customer record associated with this question is missing.", 404)

    data = request.get_json(silent=True) or {}
    force = bool(data.get("force", False))

    # Prevent duplicate if already sent, unless force=True
    if question.email_status == "sent" and not force:
        return error_response(
            "Email notification has already been successfully accepted by the provider. Pass force=true to resend.",
            400
        )

    # Attempt send
    email_res = EmailService.send_customer_answer_email(
        customer_name=f"{customer.first_name} {customer.last_name}",
        customer_email=customer.email,
        shop_name=g.current_shop.shop_name,
        question=question.question,
        answer=question.owner_answer,
        question_id=question.id
    )

    try:
        provider_name = email_res.get("provider", "unknown")
        question.email_retries = (question.email_retries or 0) + 1
        
        if email_res.get("success"):
            question.email_status = "sent"
            question.email_error = None
            question.email_sent_at = datetime.now(timezone.utc)
            question.email_provider = provider_name
            status_code = 200
            msg = "Email notification has been submitted successfully to the customer."
        else:
            question.email_status = "failed"
            question.email_error = email_res.get("error")
            question.email_provider = provider_name
            status_code = 502
            msg = f"Email delivery failed: {email_res.get('error')}"

        notif_log = EmailNotificationLog(
            shop_id=shop_id,
            customer_question_id=question.id,
            recipient_email=customer.email,
            provider=provider_name,
            status=question.email_status,
            error_message=email_res.get("error")
        )
        db.session.add(notif_log)
        db.session.commit()

        if question.email_status == "sent":
            return success_response(question.to_dict(), msg, 200)
        else:
            return error_response(msg, status_code, errors={"email_error": email_res.get("error")})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating retry status: {e}")
        return error_response(f"Database error while recording email retry: {str(e)}", 500)

@questions_bp.route("/<int:question_id>/follow-up", methods=["POST"])
@jwt_required
def send_follow_up(question_id):
    """
    Send a follow-up response in an ongoing two-way customer email conversation.
    Appends the message to the conversation, emails the customer, and preserves full history.
    """
    shop_id = g.current_shop.id
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)

    data = request.get_json() or {}
    follow_up_text = (data.get("reply") or data.get("answer") or "").strip()
    if not follow_up_text:
        return error_response("Reply message cannot be empty.", 400)

    customer = question.customer
    if not customer:
        return error_response("Customer record associated with this question is missing.", 404)

    try:
        # 1. Save owner message in conversation thread
        if question.conversation_id:
            msg = Message(
                shop_id=shop_id,
                conversation_id=question.conversation_id,
                sender_type="owner",
                message_content=follow_up_text
            )
            db.session.add(msg)

        question.owner_answer = follow_up_text
        question.status = "answered"
        question.answered_at = datetime.now(timezone.utc)

        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="owner_follow_up",
            details=f"Owner sent follow-up response to Question #{question.id} for {customer.email}"
        )
        db.session.add(log)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return error_response(f"Database error saving follow-up reply: {str(e)}", 500)

    # 2. Dispatch follow-up email
    email_res = EmailService.send_customer_answer_email(
        customer_name=f"{customer.first_name} {customer.last_name}",
        customer_email=customer.email,
        shop_name=g.current_shop.shop_name,
        question=question.question,
        answer=follow_up_text,
        question_id=question.id,
        is_follow_up=True
    )

    try:
        provider_name = email_res.get("provider", "unknown")
        if email_res.get("success"):
            question.email_status = "sent"
            question.email_error = None
            question.email_sent_at = datetime.now(timezone.utc)
            question.email_provider = provider_name
        else:
            question.email_status = "failed"
            question.email_error = email_res.get("error")
            question.email_provider = provider_name

        question.email_retries = (question.email_retries or 0) + 1

        notif_log = EmailNotificationLog(
            shop_id=shop_id,
            customer_question_id=question.id,
            recipient_email=customer.email,
            provider=provider_name,
            status=question.email_status,
            error_message=email_res.get("error")
        )
        db.session.add(notif_log)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to record follow-up email status: {e}")

    return success_response({
        "question": question.to_dict(),
        "email_status": question.email_status,
        "email_error": question.email_error
    }, "Follow-up response saved and email notification sent to customer.")

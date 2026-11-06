from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, current_app
from backend.app.models import db, Shop, Customer, CustomerSession, Conversation, Message, CustomerQuestion, AnswerFeedback, ActivityLog
from backend.app.utils.security import generate_session_token, hash_session_token
from backend.app.utils.helpers import success_response, error_response, is_valid_email
from backend.app.services.search_service import search_shop_knowledge
from backend.app.services.ai_service import AIService, FALLBACK_MESSAGE
from backend.app.middleware.rate_limit import rate_limit

customer_bp = Blueprint("customer", __name__)

def _get_active_session_and_customer(shop_id: int, token: str):
    """Validate customer session token against shop."""
    if not token:
        return None, None
    token_hash = hash_session_token(token)
    session_obj = CustomerSession.query.filter_by(
        shop_id=shop_id,
        session_token_hash=token_hash
    ).first()
    
    if not session_obj:
        return None, None
        
    if session_obj.is_expired():
        return None, None
        
    customer = Customer.query.filter_by(id=session_obj.customer_id, shop_id=shop_id).first()
    return session_obj, customer

@customer_bp.route("/shop/<slug>", methods=["GET"])
def get_public_shop(slug):
    """Retrieve public shop info by unique slug."""
    shop = Shop.query.filter_by(slug=slug.lower().strip()).first()
    if not shop:
        return error_response(f"Shop '{slug}' not found.", 404)
        
    return success_response({
        "shop": {
            "id": shop.id,
            "shop_name": shop.shop_name,
            "slug": shop.slug,
            "description": shop.description,
            "logo_url": shop.logo_url
        }
    })

@customer_bp.route("/shop/<slug>/session", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60)
def create_customer_session(slug):
    """Create a 36-hour customer session before asking questions."""
    shop = Shop.query.filter_by(slug=slug.lower().strip()).first()
    if not shop:
        return error_response(f"Shop '{slug}' not found.", 404)
        
    data = request.get_json() or {}
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    
    if not first_name:
        return error_response("First name is required.", 400)
    if not last_name:
        return error_response("Last name is required.", 400)
    if not email or not is_valid_email(email):
        return error_response("A valid email address is required.", 400)
        
    try:
        # Find or create customer within this specific shop
        customer = Customer.query.filter_by(shop_id=shop.id, email=email).first()
        if not customer:
            customer = Customer(
                shop_id=shop.id,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            db.session.add(customer)
            db.session.flush()
        else:
            # Update name if changed
            customer.first_name = first_name
            customer.last_name = last_name
            
        # Create session with 36h expiration
        session_duration_hours = current_app.config.get("CUSTOMER_SESSION_HOURS", 36)
        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=session_duration_hours)
        
        session_obj = CustomerSession(
            shop_id=shop.id,
            customer_id=customer.id,
            session_token_hash=token_hash,
            expires_at=expires_at
        )
        db.session.add(session_obj)
        db.session.flush()
        
        # Create or link active conversation
        conversation = Conversation(
            shop_id=shop.id,
            customer_id=customer.id,
            session_id=session_obj.id
        )
        db.session.add(conversation)
        db.session.commit()
        
        return success_response({
            "session_token": raw_token,
            "expires_at": expires_at.isoformat(),
            "customer": customer.to_dict(),
            "conversation_id": conversation.id
        }, "Customer session established", 201)
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to initialize session: {str(e)}", 500)

@customer_bp.route("/shop/<slug>/session/validate", methods=["GET"])
def validate_session(slug):
    """Check if existing session token is valid and return chat history if valid."""
    shop = Shop.query.filter_by(slug=slug.lower().strip()).first()
    if not shop:
        return error_response("Shop not found.", 404)
        
    token = request.headers.get("X-Customer-Session") or request.args.get("session_token")
    session_obj, customer = _get_active_session_and_customer(shop.id, token)
    
    if not session_obj or not customer:
        return error_response("Session expired or invalid.", 401, {"requires_reauth": True})
        
    # Get last conversation for this session
    conv = Conversation.query.filter_by(shop_id=shop.id, session_id=session_obj.id).order_by(Conversation.created_at.desc()).first()
    messages = []
    if conv:
        messages = [m.to_dict() for m in conv.messages]
        
    return success_response({
        "valid": True,
        "customer": customer.to_dict(),
        "expires_at": session_obj.expires_at.isoformat() if session_obj.expires_at else None,
        "conversation_id": conv.id if conv else None,
        "messages": messages
    })

@customer_bp.route("/shop/<slug>/chat", methods=["POST"])
@rate_limit(max_requests=40, window_seconds=60)
def chat(slug):
    """
    Handle customer question.
    Strict tenant isolation: retrieves knowledge ONLY for this shop.
    If knowledge is insufficient, returns exact fallback and marks question as Pending.
    """
    shop = Shop.query.filter_by(slug=slug.lower().strip()).first()
    if not shop:
        return error_response(f"Shop '{slug}' not found.", 404)
        
    data = request.get_json() or {}
    message_text = data.get("message", "").strip()
    token = request.headers.get("X-Customer-Session") or data.get("session_token")
    
    if not message_text:
        return error_response("Message cannot be empty.", 400)
        
    session_obj, customer = _get_active_session_and_customer(shop.id, token)
    if not session_obj or not customer:
        return error_response("Your session has expired. Please enter your name and email again.", 401, {"requires_reauth": True})
        
    # Get or create conversation
    conv = Conversation.query.filter_by(shop_id=shop.id, session_id=session_obj.id).order_by(Conversation.created_at.desc()).first()
    if not conv:
        conv = Conversation(
            shop_id=shop.id,
            customer_id=customer.id,
            session_id=session_obj.id
        )
        db.session.add(conv)
        db.session.flush()

    # Prevent accidental duplicate submissions within 3 seconds
    last_cust_msg = Message.query.filter_by(
        shop_id=shop.id,
        conversation_id=conv.id,
        sender_type="customer"
    ).order_by(Message.created_at.desc()).first()

    if last_cust_msg and last_cust_msg.message_content.strip().lower() == message_text.lower():
        now_utc = datetime.now(timezone.utc)
        created_utc = last_cust_msg.created_at.replace(tzinfo=timezone.utc) if last_cust_msg.created_at.tzinfo is None else last_cust_msg.created_at
        if (now_utc - created_utc).total_seconds() < 3:
            last_ai_msg = Message.query.filter_by(
                shop_id=shop.id,
                conversation_id=conv.id,
                sender_type="ai"
            ).order_by(Message.created_at.desc()).first()
            if last_ai_msg:
                last_q = CustomerQuestion.query.filter_by(shop_id=shop.id, conversation_id=conv.id).order_by(CustomerQuestion.created_at.desc()).first()
                return success_response({
                    "answer": last_ai_msg.message_content,
                    "status": last_q.status if last_q else "answered",
                    "can_answer": bool(last_q and last_q.status == "answered"),
                    "question_id": last_q.id if last_q else None,
                    "message_id": last_ai_msg.id,
                    "timestamp": last_ai_msg.created_at.isoformat()
                })

    # Save customer message
    cust_msg = Message(
        shop_id=shop.id,
        conversation_id=conv.id,
        sender_type="customer",
        message_content=message_text
    )
    db.session.add(cust_msg)
    db.session.flush()

    # Retrieve recent conversation history for follow-up context
    recent_msgs = Message.query.filter_by(
        shop_id=shop.id,
        conversation_id=conv.id
    ).order_by(Message.created_at.desc()).limit(6).all()
    conv_history = [
        {"sender_type": m.sender_type, "message_content": m.message_content}
        for m in reversed(recent_msgs) if m.id != cust_msg.id
    ]

    # Retrieve relevant knowledge ONLY for this shop
    relevant_knowledge = search_shop_knowledge(shop.id, message_text, min_score=0.35, limit=5)

    # Process with AI Service
    ai_result = AIService.answer_question(
        message_text,
        relevant_knowledge,
        shop.shop_name,
        conversation_history=conv_history
    )

    # Strict server-side validation: never save or return empty or null AI responses
    can_answer = bool(ai_result.get("can_answer", False))
    raw_answer = ai_result.get("answer")

    if not raw_answer or not isinstance(raw_answer, str) or not raw_answer.strip():
        can_answer = False
        final_answer = FALLBACK_MESSAGE
    else:
        final_answer = raw_answer.strip()

    if final_answer == FALLBACK_MESSAGE or len(final_answer) < 3:
        can_answer = False
        final_answer = FALLBACK_MESSAGE

    # Create Customer Question record
    status = "answered" if can_answer else "pending"
    question_record = CustomerQuestion(
        shop_id=shop.id,
        customer_id=customer.id,
        conversation_id=conv.id,
        question=message_text,
        ai_answer=final_answer if can_answer else None,
        owner_answer=None,
        status=status,
        email_status="pending" if not can_answer else "not_applicable",
        answered_at=datetime.now(timezone.utc) if can_answer else None
    )
    db.session.add(question_record)
    db.session.flush()

    # Save AI message in conversation
    ai_msg = Message(
        shop_id=shop.id,
        conversation_id=conv.id,
        sender_type="ai",
        message_content=final_answer
    )
    db.session.add(ai_msg)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to record message: {str(e)}", 500)

    return success_response({
        "answer": final_answer,
        "status": status,
        "can_answer": can_answer,
        "question_id": question_record.id,
        "message_id": ai_msg.id,
        "timestamp": ai_msg.created_at.isoformat()
    })

@customer_bp.route("/shop/<slug>/feedback", methods=["POST"])
@rate_limit(max_requests=60, window_seconds=60)
def submit_public_feedback(slug):
    """
    Allow customers to rate AI-generated answers directly in the chatbot.
    Saves positive or negative feedback in the database and updates dashboard counters.
    """
    shop = Shop.query.filter_by(slug=slug.lower().strip()).first()
    if not shop:
        return error_response(f"Shop '{slug}' not found.", 404)

    data = request.get_json() or {}
    question_id = data.get("question_id")
    feedback_type = (data.get("feedback_type") or "").strip().lower()
    comment = data.get("comment", "").strip()

    if not question_id:
        return error_response("question_id is required.", 400)
    if feedback_type not in ("good", "bad"):
        return error_response("feedback_type must be either 'good' or 'bad'.", 400)

    # Validate active customer session
    token = request.headers.get("X-Customer-Session") or data.get("session_token")
    session_obj, customer = _get_active_session_and_customer(shop.id, token)
    if not session_obj or not customer:
        return error_response("Your session has expired. Please refresh the page.", 401, {"requires_reauth": True})

    # Validate question belongs to this shop (strict tenant isolation)
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop.id).first()
    if not question:
        return error_response("Question not found or unauthorized for this shop.", 404)

    # Only eligible AI answers can be rated (not pending fallback, not owner answer)
    if not question.ai_answer or question.status != "answered":
        return error_response("Only eligible AI-generated answers can be rated.", 400)

    try:
        # Check if feedback already recorded for this question
        existing_fb = AnswerFeedback.query.filter_by(
            shop_id=shop.id,
            customer_question_id=question.id
        ).first()

        if existing_fb:
            # Allow changing rating
            existing_fb.feedback_type = feedback_type
            if comment:
                existing_fb.reason = comment
            fb_record = existing_fb
        else:
            fb_record = AnswerFeedback(
                shop_id=shop.id,
                customer_question_id=question.id,
                feedback_type=feedback_type,
                reason=comment if comment else None
            )
            db.session.add(fb_record)

        log = ActivityLog(
            shop_id=shop.id,
            user_id=None,
            action=f"customer_feedback_{feedback_type}",
            details=f"Customer {customer.email} rated AI answer for question #{question.id} as {feedback_type.upper()}"
        )
        db.session.add(log)
        db.session.commit()

        return success_response({
            "feedback": fb_record.to_dict(),
            "question_id": question.id,
            "feedback_type": feedback_type
        }, "Thanks for your feedback!")

    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to record customer feedback: {str(e)}", 500)



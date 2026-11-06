from flask import Blueprint, request, g
from backend.app.models import db, CustomerQuestion, AnswerFeedback, KnowledgeBase, ActivityLog
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response, error_response

feedback_bp = Blueprint("feedback", __name__)

@feedback_bp.route("", methods=["GET"])
@jwt_required
def list_feedback_items():
    """
    List AI answers and customer feedback for the shop owner to review.
    Supports filtering by rating ('good', 'bad') and search by customer question.
    Computes total good answers, total bad answers, and good answer percentage.
    """
    shop_id = g.current_shop.id
    type_filter = request.args.get("type", "").strip().lower()
    search_query = request.args.get("q", "").strip().lower()

    # Calculate summary metrics for the shop
    total_good = AnswerFeedback.query.filter_by(shop_id=shop_id, feedback_type="good").count()
    total_bad = AnswerFeedback.query.filter_by(shop_id=shop_id, feedback_type="bad").count()
    total_rated = total_good + total_bad
    good_percentage = round((total_good / total_rated) * 100, 1) if total_rated > 0 else 0.0

    # Query customer questions that have an AI answer
    query = CustomerQuestion.query.filter_by(shop_id=shop_id)\
        .filter(CustomerQuestion.ai_answer.isnot(None))

    if search_query:
        query = query.filter(CustomerQuestion.question.ilike(f"%{search_query}%"))

    questions = query.order_by(CustomerQuestion.created_at.desc()).all()

    # Convert to items, optionally filtering by feedback_type
    items = []
    for q in questions:
        q_dict = q.to_dict()
        fb_list = q_dict.get("feedback") or []
        primary_fb = fb_list[0] if fb_list else None
        rating = primary_fb.get("feedback_type") if primary_fb else "unrated"

        if type_filter and rating != type_filter:
            continue

        item_data = {
            "id": q.id,
            "question_id": q.id,
            "customer_name": q_dict.get("customer_name", "Anonymous"),
            "customer_email": q_dict.get("customer_email", "N/A"),
            "question": q.question,
            "ai_answer": q.ai_answer,
            "rating": rating,
            "feedback_type": rating,
            "feedback_comment": primary_fb.get("reason") if primary_fb else None,
            "correct_answer": primary_fb.get("correct_answer") if primary_fb else None,
            "created_at": primary_fb.get("created_at") if primary_fb else q_dict.get("created_at"),
            "has_feedback": bool(primary_fb),
            "feedback": fb_list
        }
        items.append(item_data)

    return success_response({
        "items": items,
        "total": len(items),
        "total_good": total_good,
        "total_bad": total_bad,
        "good_percentage": good_percentage
    })

@feedback_bp.route("/<int:question_id>/good", methods=["POST"])
@jwt_required
def submit_good_feedback(question_id):
    shop_id = g.current_shop.id
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)
        
    existing = AnswerFeedback.query.filter_by(customer_question_id=question.id, shop_id=shop_id).first()
    
    try:
        if existing:
            existing.feedback_type = "good"
            feedback = existing
        else:
            feedback = AnswerFeedback(
                shop_id=shop_id,
                customer_question_id=question.id,
                feedback_type="good"
            )
            db.session.add(feedback)
        
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="feedback_good",
            details=f"Marked AI answer for question #{question.id} as Good"
        )
        db.session.add(log)
        db.session.commit()
        
        return success_response(feedback.to_dict(), "Feedback saved as Good. Thank you!")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to record feedback: {str(e)}", 500)

@feedback_bp.route("/<int:question_id>/bad", methods=["POST"])
@jwt_required
def submit_bad_feedback(question_id):
    shop_id = g.current_shop.id
    question = CustomerQuestion.query.filter_by(id=question_id, shop_id=shop_id).first()
    if not question:
        return error_response("Question not found or unauthorized.", 404)
        
    data = request.get_json() or {}
    reason = data.get("reason", "").strip()
    correct_answer = data.get("correct_answer", "").strip()
    
    if not reason:
        return error_response("Please explain why this answer is bad.", 400)
    if not correct_answer:
        return error_response("Please provide the correct answer.", 400)
        
    try:
        existing = AnswerFeedback.query.filter_by(customer_question_id=question.id, shop_id=shop_id).first()
        if existing:
            existing.feedback_type = "bad"
            existing.reason = reason
            existing.correct_answer = correct_answer
            feedback = existing
        else:
            # 1. Save negative feedback
            feedback = AnswerFeedback(
                shop_id=shop_id,
                customer_question_id=question.id,
                feedback_type="bad",
                reason=reason,
                correct_answer=correct_answer
            )
            db.session.add(feedback)
        
        # 2. Add or update corrected answer in knowledge base (source_type = feedback_correction)
        kb_title = f"Correction: {question.question[:70]}"
        kb_content = f"Question: {question.question}\nCorrect Answer: {correct_answer}\nCorrection Notes: {reason}"
        
        existing_kb = KnowledgeBase.query.filter_by(
            shop_id=shop_id,
            source_type="feedback_correction",
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
                category="AI Corrections",
                source_type="feedback_correction"
            )
            db.session.add(kb_entry)
        
        # 3. Log activity
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="feedback_bad_corrected",
            details=f"Corrected AI answer for question #{question.id} and added to knowledge base"
        )
        db.session.add(log)
        
        db.session.commit()
        
        return success_response({
            "feedback": feedback.to_dict(),
            "knowledge_entry": kb_entry.to_dict()
        }, "Feedback recorded and correct answer added to Knowledge Base! Future answers will use this correction.")
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to record correction: {str(e)}", 500)


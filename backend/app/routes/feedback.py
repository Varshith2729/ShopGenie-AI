from flask import Blueprint, request, g
from backend.app.models import db, CustomerQuestion, AnswerFeedback, KnowledgeBase, ActivityLog
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response, error_response

feedback_bp = Blueprint("feedback", __name__)

@feedback_bp.route("", methods=["GET"])
@jwt_required
def list_feedback_items():
    """
    List shop owner reply feedback.
    AI answer feedback has been removed; only shop owner reply feedback is retained.
    """
    return list_owner_reply_feedback()


@feedback_bp.route("/owner-replies", methods=["GET"])
@jwt_required
def list_owner_reply_feedback():
    """
    List shop owner replies that have received customer feedback (Good / Bad).
    Includes helpfulness metrics, customer context, and search/filtering.
    """
    shop_id = g.current_shop.id
    type_filter = request.args.get("type", "").strip().lower()
    search_query = request.args.get("q", "").strip().lower()

    # Calculate summary metrics for owner replies
    total_good = AnswerFeedback.query.filter_by(shop_id=shop_id, target_type="owner_reply", feedback_type="good").count()
    total_bad = AnswerFeedback.query.filter_by(shop_id=shop_id, target_type="owner_reply", feedback_type="bad").count()
    total_rated = total_good + total_bad
    helpfulness_percentage = round((total_good / total_rated) * 100, 1) if total_rated > 0 else 0.0

    # Query owner reply feedbacks
    query = AnswerFeedback.query.filter_by(shop_id=shop_id, target_type="owner_reply")
    if type_filter in ("good", "bad"):
        query = query.filter_by(feedback_type=type_filter)

    feedbacks = query.order_by(AnswerFeedback.created_at.desc()).all()

    items = []
    for fb in feedbacks:
        fb_dict = fb.to_dict()
        if search_query:
            q_text = (fb_dict.get("question") or "").lower()
            reply_text = (fb_dict.get("owner_reply") or "").lower()
            cust_email = (fb_dict.get("customer_email") or "").lower()
            cust_name = (fb_dict.get("customer_name") or "").lower()
            if not any(search_query in field for field in (q_text, reply_text, cust_email, cust_name)):
                continue

        items.append(fb_dict)

    return success_response({
        "items": items,
        "total": len(items),
        "total_good": total_good,
        "total_bad": total_bad,
        "total_rated": total_rated,
        "helpfulness_percentage": helpfulness_percentage,
        "good_percentage": helpfulness_percentage,
        "good_owner_replies": total_good,
        "bad_owner_replies": total_bad,
        "total_owner_replies_rated": total_rated,
        "owner_helpfulness_percentage": helpfulness_percentage
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


from flask import Blueprint, g, current_app
from backend.app.models import KnowledgeBase, CustomerQuestion, AnswerFeedback, ActivityLog
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required
def get_stats():
    shop_id = g.current_shop.id
    
    total_knowledge = KnowledgeBase.query.filter_by(shop_id=shop_id).count()
    total_questions = CustomerQuestion.query.filter_by(shop_id=shop_id).count()
    pending_questions = CustomerQuestion.query.filter_by(shop_id=shop_id, status="pending").count()
    answered_questions = CustomerQuestion.query.filter_by(shop_id=shop_id, status="answered").count()
    
    # Shop Owner Reply Feedback metrics (Exclusively Owner Reply Feedback)
    total_good = AnswerFeedback.query.filter_by(shop_id=shop_id, target_type="owner_reply", feedback_type="good").count()
    total_bad = AnswerFeedback.query.filter_by(shop_id=shop_id, target_type="owner_reply", feedback_type="bad").count()
    total_rated = total_good + total_bad
    helpfulness_percentage = round((total_good / total_rated) * 100, 1) if total_rated > 0 else 0.0
    
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    public_url = f"{frontend_url}/s/{g.current_shop.slug}"
    
    return success_response({
        "stats": {
            "total_knowledge": total_knowledge,
            "total_questions": total_questions,
            "pending_questions": pending_questions,
            "answered_questions": answered_questions,
            # Owner Reply Feedback metrics
            "good_owner_replies": total_good,
            "bad_owner_replies": total_bad,
            "total_owner_replies_rated": total_rated,
            "total_owner_feedback": total_rated,
            "owner_helpfulness_percentage": helpfulness_percentage,
            "total_good": total_good,
            "total_bad": total_bad,
            "total_rated": total_rated,
            "helpfulness_percentage": helpfulness_percentage,
            "good_answers": total_good,
            "bad_answers": total_bad
        },
        "shop": g.current_shop.to_dict(),
        "public_url": public_url
    })

@dashboard_bp.route("/recent-questions", methods=["GET"])
@jwt_required
def get_recent_questions():
    shop_id = g.current_shop.id
    
    questions = CustomerQuestion.query.filter_by(shop_id=shop_id)\
        .order_by(CustomerQuestion.created_at.desc())\
        .limit(10)\
        .all()
        
    activities = ActivityLog.query.filter_by(shop_id=shop_id)\
        .order_by(ActivityLog.created_at.desc())\
        .limit(10)\
        .all()
        
    return success_response({
        "recent_questions": [q.to_dict() for q in questions],
        "recent_activities": [a.to_dict() for a in activities]
    })


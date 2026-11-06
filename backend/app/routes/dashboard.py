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
    
    good_feedback = AnswerFeedback.query.filter_by(shop_id=shop_id, feedback_type="good").count()
    bad_feedback = AnswerFeedback.query.filter_by(shop_id=shop_id, feedback_type="bad").count()
    
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    public_url = f"{frontend_url}/s/{g.current_shop.slug}"
    
    return success_response({
        "stats": {
            "total_knowledge": total_knowledge,
            "total_questions": total_questions,
            "pending_questions": pending_questions,
            "answered_questions": answered_questions,
            "good_answers": good_feedback,
            "bad_answers": bad_feedback
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


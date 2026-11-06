from flask import Blueprint, request, g
from backend.app.models import db, KnowledgeBase, ActivityLog
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response, error_response

knowledge_bp = Blueprint("knowledge", __name__)

@knowledge_bp.route("", methods=["GET"])
@jwt_required
def list_knowledge():
    shop_id = g.current_shop.id
    search_query = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "").strip()
    
    query = KnowledgeBase.query.filter_by(shop_id=shop_id)
    
    if category:
        query = query.filter_by(category=category)
        
    if search_query:
        # Search title, content, and category
        search_filter = (
            KnowledgeBase.title.ilike(f"%{search_query}%") |
            KnowledgeBase.content.ilike(f"%{search_query}%") |
            KnowledgeBase.category.ilike(f"%{search_query}%")
        )
        query = query.filter(search_filter)
        
    entries = query.order_by(KnowledgeBase.created_at.desc()).all()
    
    # Get distinct categories for filtering
    categories = [
        c[0] for c in db.session.query(KnowledgeBase.category)
        .filter_by(shop_id=shop_id)
        .distinct()
        .all()
    ]
    
    return success_response({
        "knowledge_entries": [e.to_dict() for e in entries],
        "categories": categories,
        "total": len(entries)
    })

@knowledge_bp.route("", methods=["POST"])
@jwt_required
def create_knowledge():
    shop_id = g.current_shop.id
    data = request.get_json() or {}
    
    # Support both single object and bulk array of objects
    if isinstance(data, list):
        items = data
    else:
        items = [data]
        
    if not items:
        return error_response("At least one knowledge entry is required.", 400)
        
    created_entries = []
    
    try:
        for item in items:
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            category = item.get("category", "General").strip() or "General"
            
            if not title or not content:
                return error_response("Each knowledge entry must have a title and content.", 400)
                
            entry = KnowledgeBase(
                shop_id=shop_id,
                title=title,
                content=content,
                category=category,
                source_type=item.get("source_type", "manual")
            )
            db.session.add(entry)
            created_entries.append(entry)
            
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="knowledge_created",
            details=f"Added {len(created_entries)} knowledge base entry/entries"
        )
        db.session.add(log)
        db.session.commit()
        
        return success_response(
            [e.to_dict() for e in created_entries],
            f"Successfully saved {len(created_entries)} knowledge entry/entries",
            201
        )
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to create knowledge entry: {str(e)}", 500)

@knowledge_bp.route("/<int:entry_id>", methods=["PUT"])
@jwt_required
def update_knowledge(entry_id):
    shop_id = g.current_shop.id
    # Strict tenant isolation check
    entry = KnowledgeBase.query.filter_by(id=entry_id, shop_id=shop_id).first()
    if not entry:
        return error_response("Knowledge entry not found or unauthorized.", 404)
        
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    category = data.get("category", "").strip()
    
    if not title or not content:
        return error_response("Title and content are required.", 400)
        
    try:
        entry.title = title
        entry.content = content
        if category:
            entry.category = category
            
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="knowledge_updated",
            details=f"Updated entry #{entry.id}: '{title}'"
        )
        db.session.add(log)
        db.session.commit()
        
        return success_response(entry.to_dict(), "Knowledge entry updated successfully")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to update entry: {str(e)}", 500)

@knowledge_bp.route("/<int:entry_id>", methods=["DELETE"])
@jwt_required
def delete_knowledge(entry_id):
    shop_id = g.current_shop.id
    entry = KnowledgeBase.query.filter_by(id=entry_id, shop_id=shop_id).first()
    if not entry:
        return error_response("Knowledge entry not found or unauthorized.", 404)
        
    try:
        db.session.delete(entry)
        log = ActivityLog(
            shop_id=shop_id,
            user_id=g.current_user.id,
            action="knowledge_deleted",
            details=f"Deleted knowledge entry #{entry_id}: '{entry.title}'"
        )
        db.session.add(log)
        db.session.commit()
        return success_response(None, "Knowledge entry deleted successfully")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete entry: {str(e)}", 500)


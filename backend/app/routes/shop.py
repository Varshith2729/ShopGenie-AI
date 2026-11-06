from flask import Blueprint, request, g, current_app
from backend.app.models import db, Shop, ActivityLog
from backend.app.middleware.auth_middleware import jwt_required
from backend.app.utils.helpers import success_response, error_response, slugify

shop_bp = Blueprint("shop", __name__)

@shop_bp.route("/profile", methods=["GET"])
@jwt_required
def get_profile():
    return success_response(g.current_shop.to_dict())

@shop_bp.route("/profile", methods=["PUT"])
@jwt_required
def update_profile():
    shop = g.current_shop
    data = request.get_json() or {}
    
    shop_name = data.get("shop_name", "").strip()
    description = data.get("description", "").strip()
    slug_input = data.get("slug", "").strip()
    logo_url = data.get("logo_url", "").strip()
    
    if not shop_name:
        return error_response("Shop name is required.", 400)
        
    try:
        shop.shop_name = shop_name
        shop.description = description
        shop.logo_url = logo_url
        
        if slug_input:
            new_slug = slugify(slug_input)
            if new_slug != shop.slug:
                existing = Shop.query.filter_by(slug=new_slug).first()
                if existing and existing.id != shop.id:
                    return error_response(f"The slug '{new_slug}' is already taken.", 409)
                shop.slug = new_slug
                
        log = ActivityLog(
            shop_id=shop.id,
            user_id=g.current_user.id,
            action="shop_updated",
            details="Updated shop profile settings"
        )
        db.session.add(log)
        db.session.commit()
        return success_response(shop.to_dict(), "Shop profile updated successfully")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to update profile: {str(e)}", 500)

@shop_bp.route("/public-link", methods=["GET"])
@jwt_required
def get_public_link():
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    slug = g.current_shop.slug
    public_url = f"{frontend_url}/s/{slug}"
    return success_response({
        "slug": slug,
        "public_url": public_url,
        "shop_name": g.current_shop.shop_name
    })


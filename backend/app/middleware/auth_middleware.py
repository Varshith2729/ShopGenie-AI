from functools import wraps
from flask import request, g
from backend.app.models import db, User, Shop
from backend.app.utils.security import decode_jwt_token
from backend.app.utils.helpers import error_response

def jwt_required(f):
    """Decorator to protect shop owner admin routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif "auth_token" in request.cookies:
            token = request.cookies.get("auth_token")
            
        if not token:
            return error_response("Authentication token is missing. Please log in.", 401)
            
        payload = decode_jwt_token(token)
        if not payload:
            return error_response("Invalid or expired authentication session. Please log in again.", 401)
            
        user_id = payload.get("user_id")
        user = db.session.get(User, user_id)
        if not user:
            return error_response("User account no longer exists.", 401)
            
        # Get active shop for this user
        shop = Shop.query.filter_by(owner_id=user.id).first()
        if not shop:
            return error_response("No shop associated with this owner account.", 403)
            
        g.current_user = user
        g.current_shop = shop
        return f(*args, **kwargs)
        
    return decorated_function

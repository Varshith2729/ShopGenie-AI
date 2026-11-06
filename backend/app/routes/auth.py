from flask import Blueprint, request, jsonify, g
from backend.app.models import db, User, Shop, ActivityLog
from backend.app.utils.security import hash_password, check_password, generate_jwt_token
from backend.app.utils.helpers import success_response, error_response, slugify, is_valid_email
from backend.app.middleware.auth_middleware import jwt_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    shop_name = data.get("shop_name", "").strip()
    slug_input = data.get("slug", "").strip()
    
    # Input Validation
    if not full_name:
        return error_response("Full name is required.", 400)
    if not email or not is_valid_email(email):
        return error_response("A valid email address is required.", 400)
    if not password or len(password) < 6:
        return error_response("Password must be at least 6 characters long.", 400)
    if password != confirm_password:
        return error_response("Passwords do not match.", 400)
    if not shop_name:
        return error_response("Shop name is required.", 400)
        
    slug = slugify(slug_input) if slug_input else slugify(shop_name)
    if not slug:
        return error_response("Shop slug could not be generated from the given shop name.", 400)
        
    # Check duplicate email
    if User.query.filter_by(email=email).first():
        return error_response("An account with this email already exists.", 409)
        
    # Check duplicate shop slug
    if Shop.query.filter_by(slug=slug).first():
        return error_response(f"The shop URL slug '{slug}' is already taken. Please choose another slug.", 409)
        
    try:
        # Create user
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(user)
        db.session.flush() # get user.id
        
        # Create shop
        shop = Shop(
            owner_id=user.id,
            shop_name=shop_name,
            slug=slug,
            description=data.get("description", "")
        )
        db.session.add(shop)
        db.session.flush()
        
        # Log activity
        log = ActivityLog(
            shop_id=shop.id,
            user_id=user.id,
            action="account_created",
            details=f"Owner '{full_name}' created shop '{shop_name}' ({slug})"
        )
        db.session.add(log)
        db.session.commit()
        
        token = generate_jwt_token(user.id, shop.id)
        
        return success_response({
            "token": token,
            "user": user.to_dict(),
            "shop": shop.to_dict()
        }, "Registration successful", 201)
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"Registration failed: {str(e)}", 500)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return error_response("Email and password are required.", 400)
        
    user = User.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return error_response("Invalid email or password.", 401)
        
    shop = Shop.query.filter_by(owner_id=user.id).first()
    if not shop:
        return error_response("No shop associated with this account.", 404)
        
    token = generate_jwt_token(user.id, shop.id)
    
    # Log activity
    try:
        log = ActivityLog(
            shop_id=shop.id,
            user_id=user.id,
            action="login",
            details="Owner logged in"
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    return success_response({
        "token": token,
        "user": user.to_dict(),
        "shop": shop.to_dict()
    }, "Login successful")

@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    return success_response(None, "Logged out successfully")

@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    return success_response({
        "user": g.current_user.to_dict(),
        "shop": g.current_shop.to_dict()
    })


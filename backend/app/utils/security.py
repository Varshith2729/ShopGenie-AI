import hashlib
import secrets
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from flask import current_app

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    rounds = 12
    try:
        if current_app:
            rounds = current_app.config.get("BCRYPT_ROUNDS", 12)
    except Exception:
        pass
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def generate_jwt_token(user_id: int, shop_id: int = None, expires_in_days: int = 7) -> str:
    """Generate a signed JWT token for authentication."""
    secret = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    payload = {
        "user_id": user_id,
        "shop_id": shop_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    secret = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def generate_session_token() -> str:
    """Generate a high-entropy random customer session token."""
    return secrets.token_urlsafe(48)

def hash_session_token(token: str) -> str:
    """Generate a SHA-256 hash of the customer session token for secure DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

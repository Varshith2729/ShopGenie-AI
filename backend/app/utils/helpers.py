import re
import unicodedata
from flask import jsonify

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))

def success_response(data=None, message="Success", status_code=200):
    """Standardized API success response."""
    payload = {
        "success": True,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code

def error_response(message="An error occurred", status_code=400, errors=None):
    """Standardized API error response."""
    payload = {
        "success": False,
        "message": message
    }
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status_code


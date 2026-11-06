import time
from collections import defaultdict
from functools import wraps
from flask import request, current_app
from backend.app.utils.helpers import error_response

# In-memory store for rate limiting: key -> list of request timestamps
_rate_limits = defaultdict(list)

def rate_limit(max_requests=60, window_seconds=60):
    """
    Simple in-memory rate limiting decorator.
    max_requests: maximum allowed requests per window
    window_seconds: time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_app.config.get("TESTING"):
                return f(*args, **kwargs)

            ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
            endpoint = request.endpoint or request.path
            key = f"{ip}:{endpoint}"
            
            now = time.time()
            # Clean old requests outside the window
            _rate_limits[key] = [ts for ts in _rate_limits[key] if now - ts < window_seconds]
            
            if len(_rate_limits[key]) >= max_requests:
                return error_response("Too many requests. Please slow down.", 429)
                
            _rate_limits[key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


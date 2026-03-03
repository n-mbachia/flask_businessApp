"""
Rate limiting middleware for API endpoints.
"""
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
from collections import defaultdict, deque
from typing import Dict, Deque

# In-memory rate limiter for development (replace with Redis in production)
class MemoryRateLimiter:
    """Simple in-memory rate limiter for development."""
    
    def __init__(self):
        self.requests: Dict[str, Deque] = defaultdict(deque)
        self.cleanup_interval = 3600  # Clean up old entries every hour
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit."""
        now = time.time()
        
        # Clean up old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = now
        
        # Remove old requests outside the window
        while self.requests[key] and self.requests[key][0] <= now - window:
            self.requests[key].popleft()
        
        # Check if under limit
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True
        
        return False
    
    def _cleanup(self):
        """Clean up old entries."""
        now = time.time()
        keys_to_remove = []
        
        for key, timestamps in self.requests.items():
            # Remove old timestamps
            while timestamps and timestamps[0] <= now - 3600:  # 1 hour window
                timestamps.popleft()
            
            # Mark empty keys for removal
            if not timestamps:
                keys_to_remove.append(key)
        
        # Remove empty keys
        for key in keys_to_remove:
            del self.requests[key]

# Initialize rate limiter
memory_limiter = MemoryRateLimiter()

# Flask-Limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def rate_limit(limit: str, key_func=None):
    """
    Rate limiting decorator.
    
    Args:
        limit: Rate limit string (e.g., "100 per hour", "10 per minute")
        key_func: Optional function to generate rate limit key
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Parse limit string
            try:
                count, period = limit.split()
                count = int(count)
                
                # Convert period to seconds
                if period == 'minute':
                    window = 60
                elif period == 'hour':
                    window = 3600
                elif period == 'day':
                    window = 86400
                else:
                    window = int(period)
                
            except (ValueError, IndexError):
                # Default to 100 requests per hour if parsing fails
                count, window = 100, 3600
            
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                key = f"{request.remote_addr}:{request.endpoint}"
            
            # Check rate limit
            if not memory_limiter.is_allowed(key, count, window):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit}',
                    'retry_after': window
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Predefined rate limit decorators
auth_rate_limit = rate_limit("5 per minute")
api_rate_limit = rate_limit("100 per hour")
strict_rate_limit = rate_limit("10 per minute")

def get_user_id_key():
    """Generate rate limit key based on user ID if authenticated, otherwise IP."""
    if hasattr(g, 'current_user') and g.current_user.is_authenticated:
        return f"user:{g.current_user.id}"
    return f"ip:{request.remote_addr}"

def user_rate_limit(limit: str):
    """Rate limit decorator that uses user ID when authenticated."""
    return rate_limit(limit, key_func=get_user_id_key)

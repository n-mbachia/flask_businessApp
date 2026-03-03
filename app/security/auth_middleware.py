"""
Authentication middleware for centralized security checks.
"""
import logging
from functools import wraps
from flask import request, g, current_app, abort, jsonify
from flask_login import current_user
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Centralized authentication and authorization middleware."""
    
    def __init__(self, app=None):
        """Initialize middleware with Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Execute before each request."""
        # Store request start time
        g.request_start_time = time.time()
        
        # Log request details
        self._log_request()
        
        # Check for suspicious activity
        self._check_suspicious_activity()
        
        # Validate session
        self._validate_session()
    
    def after_request(self, response):
        """Execute after each request."""
        # Add security headers
        self._add_security_headers(response)
        
        # Log response
        self._log_response(response)
        
        return response
    
    def _log_request(self):
        """Log incoming request details."""
        try:
            log_data = {
                'method': request.method,
                'url': request.url,
                'user_agent': request.headers.get('User-Agent', ''),
                'ip': request.remote_addr,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': current_user.id if current_user.is_authenticated else None
            }
            
            # Log sensitive endpoints with higher detail
            if self._is_sensitive_endpoint():
                logger.warning(f"Sensitive endpoint access: {log_data}")
            else:
                logger.info(f"Request: {log_data}")
                
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")
    
    def _log_response(self, response):
        """Log response details."""
        try:
            duration = time.time() - g.get('request_start_time', time.time())
            
            log_data = {
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'url': request.url,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Log slow requests
            if duration > 5.0:  # 5 seconds
                logger.warning(f"Slow request detected: {log_data}")
            elif response.status_code >= 400:
                logger.warning(f"Error response: {log_data}")
            else:
                logger.debug(f"Response: {log_data}")
                
        except Exception as e:
            logger.error(f"Error logging response: {str(e)}")
    
    def _check_suspicious_activity(self):
        """Check for suspicious request patterns."""
        try:
            # Check for common attack patterns
            suspicious_patterns = [
                '<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
                '../', '..\\', 'SELECT.*FROM', 'INSERT.*INTO', 'UPDATE.*SET',
                'DELETE.*FROM', 'DROP.*TABLE', 'UNION.*SELECT'
            ]
            
            request_data = f"{request.url} {request.get_data(as_text=True)}"
            
            for pattern in suspicious_patterns:
                if pattern.lower() in request_data.lower():
                    logger.warning(f"Suspicious pattern detected: {pattern} in {request.url}")
                    # Could implement IP blocking here
                    break
            
            # Check for unusual user agents
            user_agent = request.headers.get('User-Agent', '')
            if not user_agent or len(user_agent) < 10:
                logger.warning(f"Suspicious user agent: {user_agent} from {request.remote_addr}")
            
            # Check for rapid requests
            last_request_time = g.get('last_request_time')
            if last_request_time:
                time_diff = time.time() - last_request_time
                if time_diff < 0.1:  # Less than 100ms between requests
                    logger.warning(f"Rapid requests detected from {request.remote_addr}")
            
            g.last_request_time = time.time()
            
        except Exception as e:
            logger.error(f"Error checking suspicious activity: {str(e)}")
    
    def _validate_session(self):
        """Validate session integrity."""
        try:
            if current_user.is_authenticated:
                # Check session age
                if hasattr(current_user, 'last_login'):
                    last_login = current_user.last_login
                    if last_login:
                        session_age = datetime.utcnow() - last_login
                        if session_age > timedelta(hours=24):
                            logger.warning(f"Long-lived session detected for user {current_user.id}")
                
                # Check for session fixation
                session_id = session.get('_id')
                if session_id and hasattr(current_user, 'session_id'):
                    if session_id != current_user.session_id:
                        logger.error(f"Session fixation attempt for user {current_user.id}")
                        abort(401, description="Session invalid")
                        
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
    
    def _add_security_headers(self, response):
        """Add additional security headers."""
        try:
            # Remove server information
            response.headers.pop('Server', None)
            
            # Add timing headers to prevent timing attacks
            response.headers['X-DNS-Prefetch-Control'] = 'off'
            response.headers['X-Download-Options'] = 'noopen'
            response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
        except Exception as e:
            logger.error(f"Error adding security headers: {str(e)}")
    
    def _is_sensitive_endpoint(self) -> bool:
        """Check if current endpoint is sensitive."""
        sensitive_endpoints = [
            'auth.login', 'auth.register', 'auth.reset_password',
            'admin', 'settings', 'profile', 'api.users', 'api.orders'
        ]
        
        return any(endpoint in request.endpoint for endpoint in sensitive_endpoints)


def rate_limit_custom(limit: str, scope: str = None):
    """
    Custom rate limiting decorator.
    
    Args:
        limit: Rate limit string (e.g., "5/minute")
        scope: Custom scope for rate limiting
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implementation would depend on Flask-Limiter
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_json_schema(schema: dict):
    """
    Decorator to validate JSON request body against schema.
    
    Args:
        schema: JSON schema for validation
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                abort(400, description="JSON content required")
            
            try:
                data = request.get_json()
                # Schema validation logic here
                # Could use jsonschema library
                return f(*args, **kwargs)
            except Exception as e:
                abort(400, description=f"Invalid JSON: {str(e)}")
        return decorated_function
    return decorator


def log_activity(action: str, details: dict = None):
    """
    Decorator to log user activities.
    
    Args:
        action: Action description
        details: Additional details to log
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                log_data = {
                    'user_id': current_user.id,
                    'action': action,
                    'ip': request.remote_addr,
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': details or {}
                }
                logger.info(f"User activity: {log_data}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

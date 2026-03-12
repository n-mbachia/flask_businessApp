"""Security-related configurations including CSP and security headers."""
import os
import secrets
from datetime import timedelta
from functools import wraps
from flask import Flask, request, g, session, current_app, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from .utils import SecurityUtils

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration class."""
    
    # CSP Configuration
    CSP_SCRIPT_SRC = [
        "'self'",
        "'strict-dynamic'",  # Better than unsafe-inline
        "https://code.jquery.com",
        "https://cdn.jsdelivr.net",
        "https://cdn.datatables.net",
        "https://www.googletagmanager.com", 
        "https://www.google-analytics.com",
        "https://www.google.com",
        "https://www.gstatic.com",
        "http://127.0.0.1:5000",
        "https:"
    ]
    
    CSP_STYLE_SRC = [
        "'self'",
        "'unsafe-inline'",  # Required for some CSS frameworks
        "https://cdn.jsdelivr.net",
        "https://cdn.datatables.net",
        "https://fonts.googleapis.com",
        "https://use.fontawesome.com"
    ]
    
    CSP_IMG_SRC = [
        "'self'",
        "data:",
        "https:",
        "http:"
    ]
    
    CSP_FONT_SRC = [
        "'self'",
        "https://fonts.gstatic.com",
        "https://use.fontawesome.com",
        "data:"
    ]
    
    CSP_CONNECT_SRC = [
        "'self'",
        "https://www.google-analytics.com",
        "http://127.0.0.1:5000",
        "ws://127.0.0.1:5000",
        "wss://127.0.0.1:5000"
    ]
    
    # Rate limiting
    RATE_LIMIT_DEFAULT = "100/hour"
    RATE_LIMIT_AUTH = "5/minute"
    RATE_LIMIT_API = "1000/hour"


def setup_security_headers(app: Flask) -> Flask:
    """
    Configure security headers and Content Security Policy.
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask: Configured Flask application
    """
    @app.after_request
    def add_security_headers(response):
        # Generate nonce for inline scripts
        nonce = secrets.token_urlsafe(16)
        
        # Build CSP policy
        csp_policy = build_csp_policy(nonce)
        
        # Set security headers
        response.headers['Content-Security-Policy'] = csp_policy
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy-Report-Only'] = 'false'
        
        # Store nonce in g for use in templates
        g.csp_nonce = nonce
        return response
    
    return app


def build_csp_policy(nonce: str) -> str:
    """
    Build Content Security Policy string.
    
    Args:
        nonce: Cryptographic nonce for inline scripts
        
    Returns:
        str: CSP policy string
    """
    return (
        f"default-src 'self'; "
        f"script-src {' '.join(SecurityConfig.CSP_SCRIPT_SRC)} 'nonce-{nonce}'; "
        f"style-src {' '.join(SecurityConfig.CSP_STYLE_SRC)}; "
        f"img-src {' '.join(SecurityConfig.CSP_IMG_SRC)}; "
        f"font-src {' '.join(SecurityConfig.CSP_FONT_SRC)}; "
        f"connect-src {' '.join(SecurityConfig.CSP_CONNECT_SRC)}; "
        f"object-src 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'; "
        f"frame-ancestors 'none'; "
        f"upgrade-insecure-requests;"
    )


def setup_rate_limiting(app: Flask) -> Limiter:
    """
    Setup rate limiting for the application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Limiter: Configured rate limiter instance
    """
    try:
        limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=[SecurityConfig.RATE_LIMIT_DEFAULT],
            storage_uri="memory://",
            headers_enabled=True
        )
        
        # Custom rate limits for different endpoints
        @app.before_request
        def check_rate_limits():
            if request.endpoint and 'auth' in request.endpoint:
                # Stricter limits for auth endpoints
                limiter.limit(SecurityConfig.RATE_LIMIT_AUTH)
            elif request.endpoint and 'api' in request.endpoint:
                # API limits
                limiter.limit(SecurityConfig.RATE_LIMIT_API)
        
        logger.info("Rate limiting configured successfully")
        return limiter
        
    except Exception as e:
        logger.error(f"Failed to setup rate limiting: {str(e)}")
        # Return a mock limiter to avoid breaking the app
        return None


def setup_csrf_protection(app: Flask) -> Flask:
    """
    Setup CSRF protection for the application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask: Configured Flask application
    """
    try:
        from flask_wtf.csrf import CSRFProtect
        
        csrf = CSRFProtect(app)
        
        # Custom CSRF token validation
        @app.before_request
        def csrf_protect():
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                if not request.is_json and not request.form.get('csrf_token'):
                    # Check for CSRF token in non-API requests
                    if request.endpoint and not request.endpoint.startswith('api.'):
                        abort(403, description="CSRF token missing")
        
        logger.info("CSRF protection configured successfully")
        return app
        
    except ImportError:
        logger.warning("Flask-WTF not installed, CSRF protection disabled")
        return app
    except Exception as e:
        logger.error(f"Failed to setup CSRF protection: {str(e)}")
        return app


def setup_session_security(app: Flask) -> Flask:
    """
    Setup secure session configuration.
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask: Configured Flask application
    """
    # Session security settings
    app.config.update(
        SESSION_COOKIE_SECURE=True,  # Only send over HTTPS
        SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access
        SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),  # Short session lifetime
        SESSION_REFRESH_EACH_REQUEST=True,  # Refresh session on each request
    )
    
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    logger.info("Session security configured successfully")
    return app


def require_auth(f):
    """
    Decorator to require authentication for routes.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function with authentication check
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401, description="Authentication required")
        return f(*args, **kwargs)
    return decorated_function


def require_role(required_role: str):
    """
    Decorator to require specific role for routes.
    
    Args:
        required_role: Required role name
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401, description="Authentication required")
            
            if not hasattr(current_user, 'role') or current_user.role != required_role:
                abort(403, description=f"Role '{required_role}' required")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def init_security(app: Flask) -> Flask:
    """
    Initialize all security configurations.
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask: Fully configured Flask application
    """
    logger.info("Initializing security configurations...")
    
    # Setup security headers
    setup_security_headers(app)
    
    # Setup rate limiting
    setup_rate_limiting(app)
    
    # Setup CSRF protection
    setup_csrf_protection(app)
    
    # Setup session security
    setup_session_security(app)
    
    logger.info("Security initialization complete")
    return app

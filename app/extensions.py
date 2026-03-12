import os
import sentry_sdk
from flask import g
from sentry_sdk.integrations.flask import FlaskIntegration
from . import db, login_manager, migrate, compress, csrf, mail, cache

def configure_extensions(app):
    """Configure Flask extensions."""
    # Initialize Sentry for error tracking if DSN is provided
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0
        )
    
    # Configure email settings
    app.config.setdefault('MAIL_SERVER', 'smtp.gmail.com')
    app.config.setdefault('MAIL_PORT', 587)
    app.config.setdefault('MAIL_USE_TLS', True)
    app.config.setdefault('MAIL_USERNAME', '')
    app.config.setdefault('MAIL_PASSWORD', '')
    app.config.setdefault('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    app.config.setdefault('MAIL_DEBUG', app.debug)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    compress.init_app(app)
    
    # Configure cache
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    cache_config.update(app.config.get_namespace('CACHE_'))
    cache.init_app(app, config=cache_config)
    
    # Test cache
    with app.app_context():
        try:
            cache.set('test_key', 'test_value', timeout=5)
            assert cache.get('test_key') == 'test_value'
            app.logger.info("Cache initialized successfully")
        except Exception as e:
            app.logger.error(f"Cache initialization failed: {str(e)}")
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Configure Content Security Policy with nonce for scripts
    @app.after_request
    def add_security_headers(response):
        nonce = os.urandom(16).hex()
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' 'strict-dynamic' 'nonce-{nonce}' "
            f"https://code.jquery.com https://cdn.jsdelivr.net https://cdn.datatables.net "
            f"https://www.googletagmanager.com https://www.google-analytics.com "
            f"https://www.google.com https://www.gstatic.com http://127.0.0.1:5000 https:; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.datatables.net "
            f"https://fonts.googleapis.com https://use.fontawesome.com; "
            f"img-src 'self' data: https: http:; "
            f"font-src 'self' https://fonts.gstatic.com https://use.fontawesome.com data:; "
            f"connect-src 'self' https://www.google-analytics.com http://127.0.0.1:5000 "
            f"ws://127.0.0.1:5000 wss://127.0.0.1:5000; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"frame-ancestors 'none';"
        )
        
        response.headers['Content-Security-Policy'] = csp_policy
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Store nonce in g for use in templates
        g.csp_nonce = nonce
        return response
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.query.get(int(user_id))

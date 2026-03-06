"""
Application factory for the Flask application.
"""
import os
from flask import Flask, request, jsonify, current_app, session
try:
    from flask_caching import Cache
    _HAS_FLASK_CACHING = True
except ImportError:
    Cache = None
    _HAS_FLASK_CACHING = False
from flask_compress import Compress
from flask_login import LoginManager
try:
    from flask_mail import Mail
    _HAS_FLASK_MAIL = True
except ImportError:
    Mail = None
    _HAS_FLASK_MAIL = False
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from config import Config
from .assets import ensure_tailwind_built
try:
    from flask_socketio import SocketIO
    _HAS_FLASK_SOCKETIO = True
except ImportError:
    SocketIO = None
    _HAS_FLASK_SOCKETIO = False

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# Null object pattern for optional extensions
class _NullMail:
    def init_app(self, app):
        app.logger.warning('Flask-Mail not installed; email sending disabled.')
    
    def send(self, message):
        app.logger.warning(f'Mail not sent (Flask-Mail not installed): {getattr(message, "subject", "unknown")}')

class _NullCache:
    def init_app(self, app, config=None):
        app.logger.warning('Flask-Caching not installed; cache features disabled.')
    
    def get(self, *args, **kwargs): return None
    def set(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass
    def cached(self, *args, **kwargs):
        def decorator(f): return f
        return decorator

class _NullSocketIO:
    def init_app(self, app, **kwargs):
        app.logger.warning('Flask-SocketIO not installed; realtime features disabled.')
    
    def on(self, event, *args, **kwargs):
        def decorator(f): return f
        return decorator
    
    def emit(self, *args, **kwargs): pass
    def broadcast(self, *args, **kwargs): pass

# Handle optional extensions with consistent null object pattern
mail = Mail() if _HAS_FLASK_MAIL else _NullMail()
cache = Cache() if _HAS_FLASK_CACHING else _NullCache()
socketio = SocketIO() if _HAS_FLASK_SOCKETIO else _NullSocketIO()

compress = Compress()
csrf = CSRFProtect()
cors = CORS()


def create_app(config_name='default'):
    """Application factory function."""
    from config import config

    # Initialize app
    app = Flask(__name__, static_folder='static')

    # Load configuration
    if isinstance(config_name, str):
        config_class = config.get(config_name, config['default'])
        app.config.from_object(config_class)
        if hasattr(config_class, 'init_app'):
            config_class.init_app(app)
    elif isinstance(config_name, type):
        app.config.from_object(config_name)
        if hasattr(config_name, 'init_app'):
            config_name.init_app(app)
    elif isinstance(config_name, object):
        app.config.from_object(config_name)
        if hasattr(config_name, 'init_app'):
            config_name.init_app(app)
    else:
        default_cfg = config['default']
        app.config.from_object(default_cfg)
        default_cfg.init_app(app)

    # CRITICAL: Ensure SQLALCHEMY_DATABASE_URI is set before db.init_app
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError(
            "SQLALCHEMY_DATABASE_URI must be set in configuration. "
            "Check that your config class defines this attribute."
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    compress.init_app(app)
    
    # Configure CORS with restrictive defaults
    cors_origins = app.config.get('CORS_ALLOWED_ORIGINS', 
                                  ['http://localhost:3000', 'http://127.0.0.1:3000'] if app.debug else [])
    cors.init_app(app, resources={
        r"/api/*": {"origins": cors_origins, "supports_credentials": True},
        r"/socket.io/*": {"origins": cors_origins} if _HAS_FLASK_SOCKETIO else {}
    })
    
    socketio.init_app(
        app,
        cors_allowed_origins=cors_origins or "*",
        async_mode='threading',
        logger=app.debug,
        engineio_logger=app.debug
    )

    # Configure session settings
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', not app.debug)
    app.config['SESSION_COOKIE_HTTPONLY'] = app.config.get('SESSION_COOKIE_HTTPONLY', True)
    app.config['SESSION_COOKIE_SAMESITE'] = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('PERMANENT_SESSION_LIFETIME', 3600)

    # Secure logging - never expose SECRET_KEY
    if app.debug:
        app.logger.debug("SECRET_KEY configured: [MASKED]")
        app.logger.debug(f"SESSION_COOKIE_SECURE: {app.config['SESSION_COOKIE_SECURE']}")
        app.logger.debug(f"SESSION_COOKIE_DOMAIN: {app.config.get('SESSION_COOKIE_DOMAIN', 'Not set')}")
    
    # Configure cache
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    cache_config.update(app.config.get_namespace('CACHE_'))
    cache.init_app(app, config=cache_config)

    # Register request hooks
    _register_request_hooks(app)

    # Register user loader
    _register_user_loader(app)

    # Register blueprints
    register_blueprints(app)

    # Register CLI commands (modular)
    from app.cli import register_all_commands
    register_all_commands(app)

    # Register Socket.IO handlers
    _register_socketio_handlers(app)

    # Allow both trailing and non-trailing slash routes without redirect
    app.url_map.strict_slashes = False

    # Configure logging
    from .utils import configure_logging
    configure_logging(app)

    # Register context processors
    from .utils import register_context_processors
    register_context_processors(app)

    # Register template filters
    from .utils import register_template_filters
    register_template_filters(app)

    # Register error handlers
    from .utils import register_error_handlers
    register_error_handlers(app)

    # Initialize database and create analytics views
    _initialize_database(app)

    # Add static file versioning in development
    if app.config.get('DEBUG'):
        @app.context_processor
        def inject_debug():
            import time
            return dict(static_version=time.time())

    return app


def _register_request_hooks(app):
    """Register before_request and teardown hooks."""
    
    @app.before_request
    def check_db_before_request():
        try:
            db.session.execute(text('SELECT 1'))
            app.logger.debug("Database connection is healthy before request.")
        except Exception as e:
            app.logger.error(f"Database connection is BROKEN before request: {e}")

    @app.before_request
    def log_request_info():
        """Log details of every request to help trace transaction issues."""
        app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            safe_data = {}
            try:
                if request.is_json:
                    safe_data = request.get_json(silent=True) or {}
                else:
                    safe_data = request.form.to_dict()
                
                # Sanitize sensitive fields
                sensitive_fields = {'password', 'password_hash', 'token', 'secret', 'api_key', 'credit_card', 'ssn'}
                for field in sensitive_fields:
                    if field in safe_data:
                        safe_data[field] = '[FILTERED]'
            except Exception as e:
                safe_data = f"<unable to parse: {e}>"
            
            app.logger.info(f"Request data: {safe_data}")
    
    @app.before_request
    def clear_stale_transaction():
        """Roll back any stale transaction before processing the request."""
        try:
            if db.session.is_active:
                db.session.rollback()
                app.logger.debug("Rolled back stale transaction")
        except Exception as e:
            app.logger.error(f"Failed to roll back stale transaction: {e}")
        
        # Debug session contents (only in development)
        if app.debug and app.config.get('LOG_SESSION_CONTENT'):
            app.logger.debug(f"Session contents: {dict(session)}")
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Automatically clean up the session after each request."""
        if exception:
            app.logger.error(f"Teardown called with exception: {exception}")
        
        try:
            if db.session.is_active:
                db.session.rollback()
                app.logger.debug("Session rolled back in teardown.")
        except Exception as e:
            app.logger.error(f"Rollback failed in teardown: {e}")
            try:
                db.session.close()
            except Exception as close_error:
                app.logger.critical(f"Failed to close session: {close_error}")
        finally:
            db.session.remove()


def _register_user_loader(app):
    """Register Flask-Login user loader."""
    # Cache the import to avoid repeated imports
    _user_model = None
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        nonlocal _user_model
        if _user_model is None:
            from .models.users import User
            _user_model = User
        return db.session.get(_user_model, int(user_id))


def _register_socketio_handlers(app):
    """Register Socket.IO handlers if available."""
    if not _HAS_FLASK_SOCKETIO:
        return
        
    try:
        from app.services.socketio_handlers import (
            register_socketio_events,
            init_realtime_dashboard
        )
        register_socketio_events(socketio)
        realtime_service = init_realtime_dashboard(socketio)
        app.extensions['realtime_dashboard'] = realtime_service
        app.logger.info("Socket.IO initialized successfully.")
    except Exception as e:
        app.logger.error(f"Socket.IO initialization failed: {e}", exc_info=True)


def _initialize_database(app):
    """Initialize database and create analytics views."""
    with app.app_context():
        from .models import init_db, create_analytics_views
        init_db(app)

        try:
            create_analytics_views()
            app.logger.info("Analytics views created successfully.")
        except Exception as e:
            app.logger.error(f"Error creating analytics views: {str(e)}")
            if app.config.get('DEBUG') and app.config.get('RAISE_ON_ANALYTICS_ERROR'):
                raise


def register_blueprints(app):
    """Register Flask blueprints by delegating to the routes package."""
    from app.routes import register_blueprints as register_routes_blueprints
    register_routes_blueprints(app)

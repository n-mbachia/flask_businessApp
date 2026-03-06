"""
Application factory for the Flask application.
"""
import os
from flask import Flask, request, jsonify, current_app, session
import click
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

# Handle optional extensions
if _HAS_FLASK_MAIL:
    mail = Mail()
else:
    class _NullMail:
        def init_app(self, app):
            app.logger.warning('Flask-Mail not installed; email sending disabled.')
    mail = _NullMail()

if _HAS_FLASK_CACHING:
    cache = Cache()
else:
    cache = None

compress = Compress()
csrf = CSRFProtect()
cors = CORS()
if _HAS_FLASK_SOCKETIO:
    socketio = SocketIO()
else:
    socketio = None

def create_app(config_name='default'):
    """Application factory function."""
    from config import config

    # Initialize app
    app = Flask(__name__, static_folder='static')

    # Load configuration
    config_map = config
    if isinstance(config_name, str):
        config_class = config_map[config_name]
    elif isinstance(config_name, type):
        config_class = config_name
    else:
        config_class = config_map['default']

    app.config.from_object(config_class)
    config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate after db
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    compress.init_app(app)
    cors.init_app(app)
    if socketio is not None:
        socketio.init_app(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=False,
            engineio_logger=False
        )

    # Configure session settings
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', False)
    app.config['SESSION_COOKIE_HTTPONLY'] = app.config.get('SESSION_COOKIE_HTTPONLY', True)
    app.config['SESSION_COOKIE_SAMESITE'] = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('PERMANENT_SESSION_LIFETIME', 3600)

    print("SECRET_KEY:", app.config['SECRET_KEY'])
    print("SESSION_COOKIE_SECURE:", app.config['SESSION_COOKIE_SECURE'])
    print("SESSION_COOKIE_DOMAIN:", app.config.get('SESSION_COOKIE_DOMAIN'))
    
    # Configure cache
    if cache is not None:
        cache_config = {
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_THRESHOLD': 1000,
        }
        cache_config.update(app.config.get_namespace('CACHE_'))
        cache.init_app(app, config=cache_config)
    else:
        app.logger.warning('Flask-Caching not installed; cache features disabled.')

    # ---- DIAGNOSTIC LOGGING: before_request hook ----
    @app.before_request
    def check_db_before_request():
        try:
            # Try a simple no-op query to test the connection
            db.session.execute(text('SELECT 1'))
            app.logger.info("Database connection is healthy before request.")
        except Exception as e:
            app.logger.error(f"Database connection is BROKEN before request: {e}")

    @app.before_request
    def log_request_info():
        """Log details of every request to help trace transaction issues."""
        app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        if request.method in ['POST', 'PUT', 'DELETE']:
            # Log form data (excluding passwords for security)
            safe_data = request.form.to_dict()
            if 'password' in safe_data:
                safe_data['password'] = '[FILTERED]'
            if 'password_hash' in safe_data:
                safe_data['password_hash'] = '[FILTERED]'
            app.logger.info(f"Request data: {safe_data}")
    
    @app.before_request
    def clear_stale_transaction():
        """Roll back any stale transaction before processing the request."""
        try:
            db.session.rollback()
        except Exception as e:
            app.logger.error(f"Failed to roll back stale transaction: {e}")
        # Debug: print session contents (only for development)
        if app.debug:
            print("Session contents:", dict(session))
    
    # ---- ENHANCED TEARDOWN: handle exceptions and clean up session ----
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Automatically clean up the session after each request.
        If an exception occurred or the session is dirty, roll back.
        If rollback fails, dispose the engine to force new connections."""
        if exception:
            app.logger.error(f"Teardown called with exception: {exception}")
        if exception or db.session.is_active:
            try:
                db.session.rollback()
                app.logger.info("Session rolled back in teardown.")
            except Exception as e:
                app.logger.error(f"Rollback failed in teardown: {e}. Disposing engine.")
                db.session.close()
                db.engine.dispose()  # Discard all connections – they will be recreated fresh
        db.session.remove()

    # Import User model here to avoid circular imports
    from .models.users import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return db.session.get(User, int(user_id))

    # Register blueprints
    register_blueprints(app)

    # Register CLI helpers (needs app context)
    register_cli_commands(app)

    # Register Socket.IO handlers and initialize realtime dashboard service.
    if socketio is not None:
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
    else:
        app.logger.warning('Flask-SocketIO not installed; realtime dashboard disabled.')

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
    with app.app_context():
        from .models import init_db, create_analytics_views
        init_db(app)

        # Create analytics views
        try:
            create_analytics_views()
            app.logger.info("Analytics views created successfully.")
        except Exception as e:
            app.logger.error(f"Error creating analytics views: {str(e)}")
            # Don't crash the app if views can't be created
            if app.config.get('DEBUG'):
                raise
        finally:
            # Force all connections to be closed – the next request will get a fresh one,
            # except for in-memory SQLite where disposing loses the schema.
            engine_url = getattr(db.engine, "url", None)
            if engine_url and engine_url.drivername == 'sqlite' and engine_url.database in (':memory:', None):
                app.logger.info("Skipping engine dispose for in-memory SQLite database.")
            else:
                db.engine.dispose()
                app.logger.info("Database engine disposed after startup.")

    # Add static file versioning in development
    if app.config.get('DEBUG'):
        @app.context_processor
        def inject_debug():
            import time
            return dict(static_version=time.time())

    return app

def register_blueprints(app):
    """Register Flask blueprints by delegating to the routes package."""
    from app.routes import register_blueprints as register_routes_blueprints
    register_routes_blueprints(app)


def register_cli_commands(app):
    """Register reusable CLI helpers."""
    from app.models import User

    @app.cli.command('create-admin')
    @click.option('--username', default='n_mbachia', help='Admin username')
    @click.option('--email', default='mnventures2024@gmail.com', help='Admin email')
    @click.option('--password', default='mn_Adm!n@2026', help='Admin password (stored securely)')
    def create_admin(username, email, password):
        """Create or update the super-user/vendor account."""
        with app.app_context():
            admin = User.query.filter((User.username == username) | (User.email == email)).first()
            if not admin:
                admin = User(username=username, email=email, is_admin=True, is_vendor=True, confirmed=True)
                admin.set_password(password)
                db.session.add(admin)
                db.session.commit()
                click.echo(f'Created admin user {username}')
                return

            admin.is_admin = True
            admin.is_vendor = True
            admin.confirmed = True
            admin.set_password(password)
            db.session.commit()
            click.echo(f'Updated admin user {username} with vendor privileges')

    @app.cli.command('tailwind-build')
    def tailwind_build():
        """Compile the Tailwind/PostCSS stylesheet."""
        ensure_tailwind_built(force=True)

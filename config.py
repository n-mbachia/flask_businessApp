"""
Application configuration module.
Loads settings from environment variables; production fails fast if required vars are missing.
"""
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent


def _resolve_database_uri(default_sqlite_name: str = "profitability.db") -> str:
    """
    Resolve DATABASE_URL, handling relative SQLite paths for development.
    In production, an absolute PostgreSQL URI is expected.
    """
    raw_uri = os.environ.get("DATABASE_URL")
    if not raw_uri:
        # Development default: SQLite relative to BASE_DIR
        return f"sqlite:///{BASE_DIR / default_sqlite_name}"

    uri = raw_uri.strip()

    # Normalize sqlite relative paths (development only)
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        sqlite_path = uri.replace("sqlite:///", "", 1).strip()
        if sqlite_path and sqlite_path != ":memory:":
            return f"sqlite:///{(BASE_DIR / sqlite_path).resolve()}"
    return uri


class Config:
    """Base configuration with secure defaults and environment-aware settings."""
    
    # Environment identifier
    ENV = 'default'
    
    # Security - fail fast in production if missing
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # Admin CLI credentials (optional, for automated deployment)
    # If not set, CLI will prompt interactively (RECOMMENDED for security)
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    
    # Database - MUST be set, either here or in subclass
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri("profitability.db")  # Default for safety
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
    }

    # Tax rate (16% default)
    SALES_TAX_RATE = float(os.environ.get("SALES_TAX_RATE", "0.16"))

    # Email confirmation requirement (defaults to off so app works out of the box)
    REQUIRE_EMAIL_CONFIRMATION = os.environ.get('REQUIRE_EMAIL_CONFIRMATION', 'false').lower() == 'true'

    # Session - secure by default, relaxed in debug
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 3600))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")

    # CORS - restrictive by default
    CORS_ALLOWED_ORIGINS = []
    CORS_SUPPORTS_CREDENTIALS = True

    # Cache (Flask‑Caching)
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))
    CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", "businessapp_")
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL")

    # Product image defaults
    DEFAULT_PRODUCT_IMAGE = 'images/default-product.png'
    PRODUCT_IMAGE_URL_PATH = 'uploads/products'
    PRODUCT_IMAGE_UPLOAD_PATH = str(BASE_DIR / 'app' / 'static' / 'uploads' / 'products')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Rate limiting (Flask‑Limiter)
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day, 50 per hour")
    RATELIMIT_AUTH_URL = os.environ.get("RATELIMIT_AUTH_URL", "5 per minute")
    RATELIMIT_API_URL = os.environ.get("RATELIMIT_API_URL", "100 per hour")

    # Email
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "on", "1")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")

    # Confirmation token configuration
    EMAIL_CONFIRMATION_SALT = os.environ.get('EMAIL_CONFIRMATION_SALT', 'businessapp-email-confirm')
    EMAIL_CONFIRMATION_EXPIRATION = int(os.environ.get('EMAIL_CONFIRMATION_EXPIRATION', 3600))

    # Debug/Logging
    LOG_SESSION_CONTENT = os.environ.get('LOG_SESSION_CONTENT', 'false').lower() == 'true'
    RAISE_ON_ANALYTICS_ERROR = os.environ.get('RAISE_ON_ANALYTICS_ERROR', 'false').lower() == 'true'

    @staticmethod
    def init_app(app):
        """Validate critical settings after config is loaded."""
        # Refresh SECRET_KEY from environment at runtime
        env_secret = os.environ.get("SECRET_KEY")
        if env_secret:
            app.config["SECRET_KEY"] = env_secret
        elif not app.config.get("SECRET_KEY"):
            if app.config.get("DEBUG") or app.config.get("TESTING"):
                import secrets
                generated_key = secrets.token_hex(32)
                app.config["SECRET_KEY"] = generated_key
                app.logger.warning(
                    "SECRET_KEY not provided; using generated fallback in debug/testing mode. "
                    f"Set SECRET_KEY={generated_key} in your .env file for persistence."
                )
            else:
                raise RuntimeError("SECRET_KEY must be set in production environment")

        # Refresh JWT_SECRET_KEY from environment or fallback to SECRET_KEY
        env_jwt = os.environ.get("JWT_SECRET_KEY")
        if env_jwt:
            app.config["JWT_SECRET_KEY"] = env_jwt
        elif not app.config.get("JWT_SECRET_KEY"):
            app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]
            if not app.config.get("DEBUG") and not app.config.get("TESTING"):
                app.logger.warning("JWT_SECRET_KEY not set; using SECRET_KEY fallback (not recommended for production)")

        # Refresh admin credentials from environment at runtime
        for key in ['ADMIN_USERNAME', 'ADMIN_EMAIL', 'ADMIN_PASSWORD']:
            env_val = os.environ.get(key)
            if env_val:
                app.config[key] = env_val

        # Check SameSite=None requires Secure
        samesite = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
        secure = app.config.get("SESSION_COOKIE_SECURE", False)
        if samesite == "None" and not secure:
            app.logger.warning(
                "SESSION_COOKIE_SAMESITE='None' requires SESSION_COOKIE_SECURE=True. "
                "Forcing SECURE=True."
            )
            app.config["SESSION_COOKIE_SECURE"] = True

        # Log configuration status (safe info only)
        app.logger.info(f"Config loaded: {app.config.get('ENV', 'unknown')}")
        app.logger.debug(f"Database URI type: {app.config.get('SQLALCHEMY_DATABASE_URI', 'unset')[:10]}...")


class DevelopmentConfig(Config):
    """Development settings – relaxed, with SQLite defaults."""
    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri("profitability.db")
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 60
    SESSION_COOKIE_SECURE = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")  # Don't default to hardcoded value
    REQUIRE_EMAIL_CONFIRMATION = False
    
    # Development CORS - common local ports
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
    ]
    
    LOG_SESSION_CONTENT = True

    @staticmethod
    def init_app(app):
        Config.init_app(app)


class TestingConfig(Config):
    """Testing – in‑memory SQLite, disable CSRF, no caching."""
    TESTING = True
    DEBUG = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = "null"
    SESSION_COOKIE_SECURE = False
    REQUIRE_EMAIL_CONFIRMATION = False
    CORS_ALLOWED_ORIGINS = ['*']  # Allow all for testing convenience

    @staticmethod
    def init_app(app):
        Config.init_app(app)


class ProductionConfig(Config):
    """Production settings – strict, require PostgreSQL & Redis."""
    DEBUG = False
    TESTING = False
    ENV = 'production'

    # Database: must be set via environment (PostgreSQL recommended)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # Secret keys: must be set (no fallbacks)
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # Cache: prefer Redis in production
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "RedisCache")
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 3600))
    CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", "prod_businessapp_")

    # Rate limiting: require shared storage (Redis)
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "redis://localhost:6379/1")

    # Session security: enforce HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 7200))

    # CORS: must be explicitly configured
    CORS_ALLOWED_ORIGINS = []

    # Email confirmation can be enabled in production
    REQUIRE_EMAIL_CONFIRMATION = os.environ.get('REQUIRE_EMAIL_CONFIRMATION', 'false').lower() == 'true'

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        errors = []
        warnings = []

        # Critical: Database
        if not ProductionConfig.SQLALCHEMY_DATABASE_URI:
            errors.append("DATABASE_URL environment variable is required")
        elif 'sqlite' in ProductionConfig.SQLALCHEMY_DATABASE_URI.lower():
            warnings.append("SQLite detected in production; PostgreSQL recommended for production use")

        # Critical: Secret keys
        if not os.environ.get("SECRET_KEY"):
            errors.append("SECRET_KEY environment variable is required")
        if not os.environ.get("JWT_SECRET_KEY"):
            warnings.append("JWT_SECRET_KEY not set; using SECRET_KEY fallback (not recommended)")

        # Conditional: Redis for cache
        cache_type = (ProductionConfig.CACHE_TYPE or "").lower()
        if cache_type in {"rediscache", "redis"} and not ProductionConfig.CACHE_REDIS_URL:
            errors.append("CACHE_REDIS_URL required when CACHE_TYPE=RedisCache")

        # Conditional: Rate limiting storage
        if not ProductionConfig.RATELIMIT_STORAGE_URL or ProductionConfig.RATELIMIT_STORAGE_URL == "memory://":
            warnings.append("RATELIMIT_STORAGE_URL using memory://; use Redis for multi-instance deployments")

        # CORS check
        if not ProductionConfig.CORS_ALLOWED_ORIGINS:
            warnings.append("CORS_ALLOWED_ORIGINS is empty; frontend requests may be blocked")

        # Admin credentials check (warn if set via env - security consideration)
        if os.environ.get("ADMIN_PASSWORD"):
            warnings.append("ADMIN_PASSWORD set via environment variable; consider using interactive mode for better security")

        # Log warnings
        for warning in warnings:
            app.logger.warning(f"Production config warning: {warning}")

        # Fail fast on errors
        if errors:
            raise RuntimeError(
                "Production configuration errors:\n" + 
                "\n".join(f"  - {err}" for err in errors)
            )

        app.logger.info("Production configuration validated successfully")


# Configuration dictionary – MUST be at module level
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

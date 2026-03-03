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
    """Base configuration with common defaults."""
    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY")          # Must be set in production
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,   # Test connection before using (helps with stale connections)
    }

    # Tax rate (16% default)
    SALES_TAX_RATE = float(os.environ.get("SALES_TAX_RATE", "0.16"))

    # Email confirmation requirement (defaults to off so app works out of the box)
    REQUIRE_EMAIL_CONFIRMATION = os.environ.get('REQUIRE_EMAIL_CONFIRMATION', 'false').lower() == 'true'

    # Session
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 3600))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")

    # Cache (Flask‑Caching)
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")          # Override in production
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))
    CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", "businessapp_")
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL")          # Required if CACHE_TYPE=RedisCache

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

    @staticmethod
    def init_app(app):
        """Validate critical settings after config is loaded."""
        # Check SameSite=None requires Secure
        samesite = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
        secure = app.config.get("SESSION_COOKIE_SECURE", False)
        if samesite == "None" and not secure:
            app.logger.warning(
                "SESSION_COOKIE_SAMESITE='None' requires SESSION_COOKIE_SECURE=True. "
                "Forcing SECURE=True."
            )
            app.config["SESSION_COOKIE_SECURE"] = True

        # Refresh SECRET_KEY at runtime so tests can override env vars before app creation
        secret_key = os.environ.get("SECRET_KEY")
        if secret_key:
            app.config["SECRET_KEY"] = secret_key
        elif not app.config.get("SECRET_KEY") and (app.config.get("DEBUG") or app.config.get("TESTING")):
            app.config["SECRET_KEY"] = "dev-secret-key"
            app.logger.warning(
                "SECRET_KEY not provided; using insecure fallback in debug/testing mode."
            )


class DevelopmentConfig(Config):
    """Development settings – relaxed, with SQLite defaults."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri("profitability.db")
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 60
    SESSION_COOKIE_SECURE = False          # Allow HTTP in development
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
    REQUIRE_EMAIL_CONFIRMATION = False     # Disable email confirmation in development

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # Optional: create tables automatically? Handled by app factory.
        pass


class TestingConfig(Config):
    """Testing – in‑memory SQLite, disable CSRF, no caching."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = "null"
    SESSION_COOKIE_SECURE = False
    REQUIRE_EMAIL_CONFIRMATION = False     # Disable for testing

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        pass


class ProductionConfig(Config):
    """Production settings – strict, require PostgreSQL & Redis."""
    DEBUG = False
    TESTING = False

    # Database: must be set via environment (PostgreSQL recommended)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # Secret keys: must be set
    SECRET_KEY = os.environ.get("SECRET_KEY")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)

    # Cache: prefer Redis (production)
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

    # Email confirmation requirement (can be overridden by env var)
    REQUIRE_EMAIL_CONFIRMATION = os.environ.get('REQUIRE_EMAIL_CONFIRMATION', 'false').lower() == 'true'

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        required = []

        if not ProductionConfig.SQLALCHEMY_DATABASE_URI:
            required.append("DATABASE_URL")
        if not ProductionConfig.SECRET_KEY:
            required.append("SECRET_KEY")

        cache_type = ProductionConfig.CACHE_TYPE or ""
        if cache_type.lower() in {"rediscache", "redis"} and not ProductionConfig.CACHE_REDIS_URL:
            required.append("CACHE_REDIS_URL")

        if ProductionConfig.RATELIMIT_STORAGE_URL is None:
            required.append("RATELIMIT_STORAGE_URL")

        if required:
            raise RuntimeError(
                "Production configuration requires the following environment variables: "
                f"{', '.join(required)}"
            )


# Configuration dictionary – MUST be at module level, outside any class
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

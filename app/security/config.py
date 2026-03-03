"""
Security configuration management for the application.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SecuritySettings:
    """Security configuration settings."""
    
    # Content Security Policy
    CSP_ENABLED: bool = True
    CSP_REPORT_ONLY: bool = False
    CSP_REPORT_URI: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/hour"
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_API: str = "1000/hour"
    RATE_LIMIT_STORAGE: str = "memory://"
    
    # Session Security
    SESSION_TIMEOUT_MINUTES: int = 60
    SESSION_SECURE: bool = True
    SESSION_HTTPONLY: bool = True
    SESSION_SAMESITE: str = "Lax"
    
    # CSRF Protection
    CSRF_ENABLED: bool = True
    CSRF_TOKEN_LENGTH: int = 32
    CSRF_TIME_LIMIT: int = 3600  # 1 hour
    
    # Password Policy
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HASH_ITERATIONS: int = 100000
    
    # Authentication
    LOGIN_ATTEMPT_LIMIT: int = 5
    LOGIN_ATTEMPT_TIMEOUT: int = 900  # 15 minutes
    PASSWORD_RESET_TIMEOUT: int = 3600  # 1 hour
    
    # Logging
    SECURITY_LOG_ENABLED: bool = True
    SECURITY_LOG_LEVEL: str = "INFO"
    AUDIT_LOG_ENABLED: bool = True
    
    # Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    
    # File Upload
    UPLOAD_MAX_SIZE: int = 16 * 1024 * 1024  # 16MB
    UPLOAD_ALLOWED_EXTENSIONS: list = None
    UPLOAD_SCAN_MALWARE: bool = False
    
    # API Security
    API_KEY_ENABLED: bool = False
    API_KEY_LENGTH: int = 64
    API_RATE_LIMIT: str = "1000/hour"
    
    # Monitoring
    ANOMALY_DETECTION: bool = True
    IP_BLACKLIST_ENABLED: bool = True
    SUSPICIOUS_ACTIVITY_THRESHOLD: int = 10
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.UPLOAD_ALLOWED_EXTENSIONS is None:
            self.UPLOAD_ALLOWED_EXTENSIONS = [
                '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt'
            ]


class SecurityConfigManager:
    """Manages security configuration from environment and files."""
    
    def __init__(self, app=None):
        """Initialize configuration manager."""
        self.settings = SecuritySettings()
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        self.load_from_environment()
        self.apply_to_app(app)
    
    def load_from_environment(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'SECURITY_CSP_ENABLED': ('CSP_ENABLED', self._parse_bool),
            'SECURITY_CSP_REPORT_ONLY': ('CSP_REPORT_ONLY', self._parse_bool),
            'SECURITY_RATE_LIMIT_ENABLED': ('RATE_LIMIT_ENABLED', self._parse_bool),
            'SECURITY_RATE_LIMIT_DEFAULT': ('RATE_LIMIT_DEFAULT', str),
            'SECURITY_RATE_LIMIT_AUTH': ('RATE_LIMIT_AUTH', str),
            'SECURITY_RATE_LIMIT_API': ('RATE_LIMIT_API', str),
            'SECURITY_SESSION_TIMEOUT': ('SESSION_TIMEOUT_MINUTES', int),
            'SECURITY_SESSION_SECURE': ('SESSION_SECURE', self._parse_bool),
            'SECURITY_SESSION_HTTPONLY': ('SESSION_HTTPONLY', self._parse_bool),
            'SECURITY_SESSION_SAMESITE': ('SESSION_SAMESITE', str),
            'SECURITY_CSRF_ENABLED': ('CSRF_ENABLED', self._parse_bool),
            'SECURITY_PASSWORD_MIN_LENGTH': ('PASSWORD_MIN_LENGTH', int),
            'SECURITY_PASSWORD_MAX_LENGTH': ('PASSWORD_MAX_LENGTH', int),
            'SECURITY_PASSWORD_REQUIRE_UPPERCASE': ('PASSWORD_REQUIRE_UPPERCASE', self._parse_bool),
            'SECURITY_PASSWORD_REQUIRE_LOWERCASE': ('PASSWORD_REQUIRE_LOWERCASE', self._parse_bool),
            'SECURITY_PASSWORD_REQUIRE_DIGIT': ('PASSWORD_REQUIRE_DIGIT', self._parse_bool),
            'SECURITY_PASSWORD_REQUIRE_SPECIAL': ('PASSWORD_REQUIRE_SPECIAL', self._parse_bool),
            'SECURITY_LOGIN_ATTEMPT_LIMIT': ('LOGIN_ATTEMPT_LIMIT', int),
            'SECURITY_LOGIN_ATTEMPT_TIMEOUT': ('LOGIN_ATTEMPT_TIMEOUT', int),
            'SECURITY_LOG_ENABLED': ('SECURITY_LOG_ENABLED', self._parse_bool),
            'SECURITY_LOG_LEVEL': ('SECURITY_LOG_LEVEL', str),
            'SECURITY_AUDIT_ENABLED': ('AUDIT_LOG_ENABLED', self._parse_bool),
            'SECURITY_HEADERS_ENABLED': ('SECURITY_HEADERS_ENABLED', self._parse_bool),
            'SECURITY_HSTS_ENABLED': ('HSTS_ENABLED', self._parse_bool),
            'SECURITY_HSTS_MAX_AGE': ('HSTS_MAX_AGE', int),
            'SECURITY_UPLOAD_MAX_SIZE': ('UPLOAD_MAX_SIZE', int),
            'SECURITY_API_KEY_ENABLED': ('API_KEY_ENABLED', self._parse_bool),
            'SECURITY_ANOMALY_DETECTION': ('ANOMALY_DETECTION', self._parse_bool),
            'SECURITY_IP_BLACKLIST_ENABLED': ('IP_BLACKLIST_ENABLED', self._parse_bool),
        }
        
        for env_var, (setting_attr, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    setattr(self.settings, setting_attr, converted_value)
                    logger.info(f"Loaded security setting {setting_attr} from environment")
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to parse {env_var}: {str(e)}")
    
    def apply_to_app(self, app):
        """Apply security settings to Flask app."""
        # Session configuration
        app.config.update({
            'SESSION_TIMEOUT_MINUTES': self.settings.SESSION_TIMEOUT_MINUTES,
            'SESSION_COOKIE_SECURE': self.settings.SESSION_SECURE,
            'SESSION_COOKIE_HTTPONLY': self.settings.SESSION_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': self.settings.SESSION_SAMESITE,
            'PERMANENT_SESSION_LIFETIME': self.settings.SESSION_TIMEOUT_MINUTES * 60,
        })
        
        # CSRF configuration
        if self.settings.CSRF_ENABLED:
            app.config.update({
                'WTF_CSRF_ENABLED': True,
                'WTF_CSRF_TIME_LIMIT': self.settings.CSRF_TIME_LIMIT,
            })
        
        # Rate limiting configuration
        if self.settings.RATE_LIMIT_ENABLED:
            app.config.update({
                'RATELIMIT_ENABLED': True,
                'RATELIMIT_DEFAULT': self.settings.RATE_LIMIT_DEFAULT,
                'RATELIMIT_STORAGE_URL': self.settings.RATE_LIMIT_STORAGE,
            })
        
        # Upload configuration
        app.config.update({
            'MAX_CONTENT_LENGTH': self.settings.UPLOAD_MAX_SIZE,
            'UPLOAD_EXTENSIONS': self.settings.UPLOAD_ALLOWED_EXTENSIONS,
        })
        
        logger.info("Security configuration applied to Flask app")
    
    def get_setting(self, setting_name: str) -> Any:
        """Get a specific security setting."""
        return getattr(self.settings, setting_name, None)
    
    def update_setting(self, setting_name: str, value: Any):
        """Update a security setting."""
        if hasattr(self.settings, setting_name):
            setattr(self.settings, setting_name, value)
            logger.info(f"Updated security setting {setting_name}")
        else:
            raise ValueError(f"Unknown security setting: {setting_name}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all security settings as dictionary."""
        return {
            attr: getattr(self.settings, attr)
            for attr in dir(self.settings)
            if not attr.startswith('_')
        }
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """Validate security settings and return any issues."""
        issues = {}
        
        # Validate password policy
        if self.settings.PASSWORD_MIN_LENGTH < 6:
            issues.setdefault('password', []).append("Password minimum length should be at least 6")
        
        if self.settings.PASSWORD_MIN_LENGTH > self.settings.PASSWORD_MAX_LENGTH:
            issues.setdefault('password', []).append("Password minimum length cannot exceed maximum length")
        
        # Validate session timeout
        if self.settings.SESSION_TIMEOUT_MINUTES < 5:
            issues.setdefault('session', []).append("Session timeout should be at least 5 minutes")
        
        if self.settings.SESSION_TIMEOUT_MINUTES > 1440:  # 24 hours
            issues.setdefault('session', []).append("Session timeout should not exceed 24 hours")
        
        # Validate rate limiting
        if self.settings.RATE_LIMIT_ENABLED:
            try:
                # Test rate limit format
                for limit_str in [self.settings.RATE_LIMIT_DEFAULT, 
                                self.settings.RATE_LIMIT_AUTH, 
                                self.settings.RATE_LIMIT_API]:
                    self._parse_rate_limit(limit_str)
            except ValueError as e:
                issues.setdefault('rate_limit', []).append(f"Invalid rate limit format: {str(e)}")
        
        # Validate file upload settings
        if self.settings.UPLOAD_MAX_SIZE < 1024:  # 1KB
            issues.setdefault('upload', []).append("Upload max size should be at least 1KB")
        
        if self.settings.UPLOAD_MAX_SIZE > 100 * 1024 * 1024:  # 100MB
            issues.setdefault('upload', []).append("Upload max size should not exceed 100MB")
        
        return issues
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean from string."""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def _parse_rate_limit(self, limit_str: str) -> tuple:
        """Parse rate limit string like '100/hour'."""
        if '/' not in limit_str:
            raise ValueError(f"Invalid rate limit format: {limit_str}")
        
        amount, period = limit_str.split('/', 1)
        try:
            amount = int(amount)
        except ValueError:
            raise ValueError(f"Invalid rate limit amount: {amount}")
        
        valid_periods = ['second', 'minute', 'hour', 'day', 'month', 'year']
        if period not in valid_periods:
            raise ValueError(f"Invalid rate limit period: {period}")
        
        return amount, period
    
    def export_config(self) -> str:
        """Export configuration as environment variables."""
        lines = ["# Security Configuration"]
        lines.append("# Copy these to your .env file")
        lines.append("")
        
        config_map = {
            'CSP_ENABLED': self.settings.CSP_ENABLED,
            'CSP_REPORT_ONLY': self.settings.CSP_REPORT_ONLY,
            'RATE_LIMIT_ENABLED': self.settings.RATE_LIMIT_ENABLED,
            'RATE_LIMIT_DEFAULT': self.settings.RATE_LIMIT_DEFAULT,
            'RATE_LIMIT_AUTH': self.settings.RATE_LIMIT_AUTH,
            'RATE_LIMIT_API': self.settings.RATE_LIMIT_API,
            'SESSION_TIMEOUT': self.settings.SESSION_TIMEOUT_MINUTES,
            'SESSION_SECURE': self.settings.SESSION_SECURE,
            'SESSION_HTTPONLY': self.settings.SESSION_HTTPONLY,
            'SESSION_SAMESITE': self.settings.SESSION_SAMESITE,
            'CSRF_ENABLED': self.settings.CSRF_ENABLED,
            'PASSWORD_MIN_LENGTH': self.settings.PASSWORD_MIN_LENGTH,
            'PASSWORD_MAX_LENGTH': self.settings.PASSWORD_MAX_LENGTH,
            'PASSWORD_REQUIRE_UPPERCASE': self.settings.PASSWORD_REQUIRE_UPPERCASE,
            'PASSWORD_REQUIRE_LOWERCASE': self.settings.PASSWORD_REQUIRE_LOWERCASE,
            'PASSWORD_REQUIRE_DIGIT': self.settings.PASSWORD_REQUIRE_DIGIT,
            'PASSWORD_REQUIRE_SPECIAL': self.settings.PASSWORD_REQUIRE_SPECIAL,
            'LOGIN_ATTEMPT_LIMIT': self.settings.LOGIN_ATTEMPT_LIMIT,
            'LOGIN_ATTEMPT_TIMEOUT': self.settings.LOGIN_ATTEMPT_TIMEOUT,
            'SECURITY_LOG_ENABLED': self.settings.SECURITY_LOG_ENABLED,
            'SECURITY_LOG_LEVEL': self.settings.SECURITY_LOG_LEVEL,
            'AUDIT_LOG_ENABLED': self.settings.AUDIT_LOG_ENABLED,
            'SECURITY_HEADERS_ENABLED': self.settings.SECURITY_HEADERS_ENABLED,
            'HSTS_ENABLED': self.settings.HSTS_ENABLED,
            'HSTS_MAX_AGE': self.settings.HSTS_MAX_AGE,
            'UPLOAD_MAX_SIZE': self.settings.UPLOAD_MAX_SIZE,
            'API_KEY_ENABLED': self.settings.API_KEY_ENABLED,
            'ANOMALY_DETECTION': self.settings.ANOMALY_DETECTION,
            'IP_BLACKLIST_ENABLED': self.settings.IP_BLACKLIST_ENABLED,
        }
        
        for key, value in config_map.items():
            lines.append(f"SECURITY_{key}={value}")
        
        return '\n'.join(lines)


# Global configuration manager instance
security_config = SecurityConfigManager()

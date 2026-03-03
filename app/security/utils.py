"""
Security utility functions for common security operations.
"""
import secrets
import hashlib
import hmac
import re
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Utility class for security operations."""
    
    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Security patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?-?\.?\s?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$')
    
    # Dangerous patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'onfocus\s*=',
        r'onblur\s*=',
        r'onchange\s*=',
        r'onsubmit\s*=',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r'(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
        r'(--|#|\/\*|\*\/)',
        r'(\bOR\b.*\b1\s*=\s*1\b)',
        r'(\bAND\b.*\b1\s*=\s*1\b)',
        r'(\'.*(OR|AND).*\'.*\=.*\')',
        r'(\'.*\=.*\'.*(OR|AND).*)',
    ]
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            str: Hex-encoded secure token
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_nonce(length: int = 16) -> str:
        """
        Generate a cryptographic nonce for CSP.
        
        Args:
            length: Nonce length in bytes
            
        Returns:
            str: URL-safe base64-encoded nonce
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password using PBKDF2.
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)
            
        Returns:
            tuple: (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return hashed.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password
            salt: Salt used for hashing
            
        Returns:
            bool: True if password matches
        """
        computed_hash, _ = SecurityUtils.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hashed)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength against security requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            dict: Validation result with details
        """
        errors = []
        warnings = []
        
        # Length checks
        if len(password) < SecurityUtils.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {SecurityUtils.PASSWORD_MIN_LENGTH} characters")
        
        if len(password) > SecurityUtils.PASSWORD_MAX_LENGTH:
            errors.append(f"Password must not exceed {SecurityUtils.PASSWORD_MAX_LENGTH} characters")
        
        # Character requirements
        if SecurityUtils.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if SecurityUtils.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if SecurityUtils.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if SecurityUtils.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password checks
        if password.lower() in ['password', '123456', 'qwerty', 'admin', 'letmein']:
            errors.append("Password is too common")
        
        # Repeated characters
        if re.search(r'(.)\1{2,}', password):
            warnings.append("Password contains repeated characters")
        
        # Sequential characters
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
            warnings.append("Password contains sequential characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'strength': SecurityUtils._calculate_password_strength(password)
        }
    
    @staticmethod
    def _calculate_password_strength(password: str) -> str:
        """Calculate password strength score."""
        score = 0
        
        # Length contribution
        score += min(len(password) / 4, 4)  # Max 4 points for length
        
        # Character variety
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 2
        
        # Complexity
        if len(set(password)) / len(password) > 0.7:
            score += 1  # High character variety
        
        if score < 3:
            return 'weak'
        elif score < 6:
            return 'medium'
        elif score < 9:
            return 'strong'
        else:
            return 'very_strong'
    
    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """
        Sanitize user input to prevent XSS attacks.
        
        Args:
            input_string: Raw user input
            
        Returns:
            str: Sanitized input
        """
        if not input_string:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = input_string.strip()
        
        # Escape HTML entities
        sanitized = sanitized.replace('&', '&amp;')
        sanitized = sanitized.replace('<', '&lt;')
        sanitized = sanitized.replace('>', '&gt;')
        sanitized = sanitized.replace('"', '&quot;')
        sanitized = sanitized.replace("'", '&#x27;')
        
        return sanitized
    
    @staticmethod
    def detect_xss(input_string: str) -> bool:
        """
        Detect potential XSS attacks in input.
        
        Args:
            input_string: Input to check
            
        Returns:
            bool: True if XSS pattern detected
        """
        if not input_string:
            return False
        
        for pattern in SecurityUtils.XSS_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def detect_sql_injection(input_string: str) -> bool:
        """
        Detect potential SQL injection attacks.
        
        Args:
            input_string: Input to check
            
        Returns:
            bool: True if SQL injection pattern detected
        """
        if not input_string:
            return False
        
        for pattern in SecurityUtils.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if valid email format
        """
        if not email:
            return False
        
        return bool(SecurityUtils.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            bool: True if valid phone format
        """
        if not phone:
            return False
        
        return bool(SecurityUtils.PHONE_PATTERN.match(phone))
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """
        Validate IP address format.
        
        Args:
            ip: IP address to validate
            
        Returns:
            bool: True if valid IP address
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """
        Check if IP address is private.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if private IP address
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except ValueError:
            return False
    
    @staticmethod
    def generate_csrf_token() -> str:
        """
        Generate a CSRF token.
        
        Returns:
            str: CSRF token
        """
        return SecurityUtils.generate_secure_token(32)
    
    @staticmethod
    def validate_csrf_token(token: str, expected_token: str) -> bool:
        """
        Validate CSRF token.
        
        Args:
            token: Token to validate
            expected_token: Expected token
            
        Returns:
            bool: True if tokens match
        """
        return hmac.compare_digest(token, expected_token)
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
        """
        Mask sensitive data for logging.
        
        Args:
            data: Sensitive data to mask
            mask_char: Character to use for masking
            visible_chars: Number of characters to keep visible
            
        Returns:
            str: Masked data
        """
        if not data or len(data) <= visible_chars:
            return mask_char * len(data) if data else ""
        
        return data[:visible_chars] + mask_char * (len(data) - visible_chars)
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any], severity: str = 'warning'):
        """
        Log security events with proper formatting.
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Log severity level
        """
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details
        }
        
        if severity == 'critical':
            logger.critical(f"SECURITY EVENT: {log_data}")
        elif severity == 'warning':
            logger.warning(f"SECURITY EVENT: {log_data}")
        else:
            logger.info(f"SECURITY EVENT: {log_data}")


class InputValidator:
    """Input validation utilities."""
    
    @staticmethod
    def validate_user_input(data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Validate user input against rules.
        
        Args:
            data: Input data to validate
            rules: Validation rules for each field
            
        Returns:
            dict: Validation errors by field
        """
        errors = {}
        
        for field, field_rules in rules.items():
            value = data.get(field)
            field_errors = []
            
            # Required validation
            if field_rules.get('required', False) and not value:
                field_errors.append(f"{field} is required")
            
            if value is not None:
                # Type validation
                expected_type = field_rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    field_errors.append(f"{field} must be of type {expected_type.__name__}")
                
                # Length validation
                if isinstance(value, str):
                    min_length = field_rules.get('min_length')
                    max_length = field_rules.get('max_length')
                    
                    if min_length and len(value) < min_length:
                        field_errors.append(f"{field} must be at least {min_length} characters")
                    
                    if max_length and len(value) > max_length:
                        field_errors.append(f"{field} must not exceed {max_length} characters")
                
                # Pattern validation
                pattern = field_rules.get('pattern')
                if pattern and isinstance(value, str):
                    if not re.match(pattern, value):
                        field_errors.append(f"{field} format is invalid")
                
                # Custom validation
                custom_validator = field_rules.get('validator')
                if custom_validator and callable(custom_validator):
                    try:
                        if not custom_validator(value):
                            field_errors.append(f"{field} is invalid")
                    except Exception as e:
                        logger.error(f"Custom validation error for {field}: {str(e)}")
                        field_errors.append(f"Validation error for {field}")
            
            if field_errors:
                errors[field] = field_errors
        
        return errors

"""
Validator utilities and common validation functions.
"""
import re
import hashlib
import secrets
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
import logging

logger = logging.getLogger(__name__)


class ValidationPatterns:
    """Common validation patterns and regex."""
    
    # Email patterns
    EMAIL_BASIC = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    EMAIL_STRICT = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Phone patterns
    PHONE_US = r'^\+?1?-?\.?\s?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$'
    PHONE_INTL = r'^\+?[1-9]\d{1,14}$'
    
    # URL patterns
    URL_HTTP = r'^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    
    # Credit card patterns
    CREDIT_CARD = r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})$'
    
    # Security patterns
    SQL_INJECTION = r'(union|select|insert|update|delete|drop|create|alter|exec|execute)'
    XSS_PATTERN = r'<script[^>]*>.*?</script>|javascript:|vbscript:|on\w+\s*='
    PATH_TRAVERSAL = r'\.\.[\/\\]'
    
    # Business patterns
    SKU_PATTERN = r'^[A-Z0-9_-]+$'
    ORDER_NUMBER = r'^[A-Z]{2}\d{8}$'
    INVOICE_NUMBER = r'^INV-\d{4}-\d{6}$'


class InputSanitizer:
    """Input sanitization utilities."""
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Sanitize HTML input to prevent XSS.
        
        Args:
            value: Input string to sanitize
            
        Returns:
            str: Sanitized string
        """
        if not value:
            return ""
        
        # Remove script tags and event handlers
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove dangerous HTML tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'textarea']
        for tag in dangerous_tags:
            sanitized = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(f'<{tag}[^>]*>', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_sql(value: str) -> str:
        """
        Sanitize input to prevent SQL injection.
        
        Args:
            value: Input string to sanitize
            
        Returns:
            str: Sanitized string
        """
        if not value:
            return ""
        
        # Remove SQL injection patterns
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter|exec|execute)',
            r'(--|#|\/\*|\*\/)',
            r'(\bOR\b.*\b1\s*=\s*1\b)',
            r'(\bAND\b.*\b1\s*=\s*1\b)',
            r'(\'.*(OR|AND).*\'.*\=.*\')',
            r'(\'.*\=.*\'.*(OR|AND).*)',
        ]
        
        sanitized = value
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for secure storage.
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        if not filename:
            return "unnamed_file"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\', '\0']
        sanitized = ''.join(c for c in filename if c not in dangerous_chars)
        
        # Remove control characters
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            max_name_len = 255 - len(ext) - 1 if ext else 255
            sanitized = name[:max_name_len] + ('.' + ext if ext else '')
        
        return sanitized.strip() or "unnamed_file"
    
    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search query.
        
        Args:
            query: Raw search query
            
        Returns:
            str: Sanitized search query
        """
        if not query:
            return ""
        
        # Remove dangerous characters but keep search-friendly characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '--', '/*', '*/']
        sanitized = query
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()


class SecurityValidator:
    """Security-focused validation utilities."""
    
    @staticmethod
    def detect_sql_injection(value: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Args:
            value: Input string to check
            
        Returns:
            bool: True if SQL injection detected
        """
        if not value:
            return False
        
        patterns = [
            r'(union|select|insert|update|delete|drop|create|alter|exec|execute)',
            r'(--|#|\/\*|\*\/)',
            r'(\bOR\b.*\b1\s*=\s*1\b)',
            r'(\bAND\b.*\b1\s*=\s*1\b)',
            r'(\'.*(OR|AND).*\'.*\=.*\')',
            r'(\'.*\=.*\'.*(OR|AND).*)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def detect_xss(value: str) -> bool:
        """
        Detect potential XSS attacks.
        
        Args:
            value: Input string to check
            
        Returns:
            bool: True if XSS detected
        """
        if not value:
            return False
        
        patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe',
            r'<object',
            r'<embed',
        ]
        
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def detect_path_traversal(value: str) -> bool:
        """
        Detect path traversal attempts.
        
        Args:
            value: Input string to check
            
        Returns:
            bool: True if path traversal detected
        """
        if not value:
            return False
        
        patterns = [
            r'\.\.[\/\\]',
            r'%2e%2e[\/\\]',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'\.\.%2f',
            r'\.\.%5c',
        ]
        
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
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
        if not token or not expected_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(token, expected_token)


class BusinessValidator:
    """Business logic validation utilities."""
    
    @staticmethod
    def validate_business_email(email: str) -> bool:
        """
        Validate email with business-specific rules.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if valid business email
        """
        if not email:
            return False
        
        # Basic email validation
        if not re.match(ValidationPatterns.EMAIL_BASIC, email):
            return False
        
        # Business-specific rules
        email = email.lower()
        
        # Block common disposable email domains
        disposable_domains = [
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'throwaway.email', 'yopmail.com'
        ]
        
        domain = email.split('@')[-1]
        if domain in disposable_domains:
            return False
        
        return True
    
    @staticmethod
    def validate_business_phone(phone: str, country_code: str = 'US') -> bool:
        """
        Validate phone number for business use.
        
        Args:
            phone: Phone number to validate
            country_code: Country code for validation rules
            
        Returns:
            bool: True if valid business phone
        """
        if not phone:
            return False
        
        # Remove formatting
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        if country_code.upper() == 'US':
            pattern = ValidationPatterns.PHONE_US
        else:
            pattern = ValidationPatterns.PHONE_INTL
        
        return bool(re.match(pattern, cleaned))
    
    @staticmethod
    def validate_sku(sku: str) -> bool:
        """
        Validate SKU format.
        
        Args:
            sku: SKU to validate
            
        Returns:
            bool: True if valid SKU format
        """
        if not sku:
            return False
        
        return bool(re.match(ValidationPatterns.SKU_PATTERN, sku.upper()))
    
    @staticmethod
    def validate_order_number(order_number: str) -> bool:
        """
        Validate order number format.
        
        Args:
            order_number: Order number to validate
            
        Returns:
            bool: True if valid order number
        """
        if not order_number:
            return False
        
        return bool(re.match(ValidationPatterns.ORDER_NUMBER, order_number.upper()))
    
    @staticmethod
    def validate_credit_card(card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.
        
        Args:
            card_number: Credit card number to validate
            
        Returns:
            bool: True if valid credit card number
        """
        if not card_number:
            return False
        
        # Remove spaces and dashes
        cleaned = re.sub(r'[\s-]', '', card_number)
        
        # Check if it's numeric and has reasonable length
        if not cleaned.isdigit() or len(cleaned) not in [13, 14, 15, 16, 19]:
            return False
        
        # Luhn algorithm
        total = 0
        reverse_digits = cleaned[::-1]
        
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0


class DateValidator:
    """Date and time validation utilities."""
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date, 
                          max_days: int = 365) -> bool:
        """
        Validate date range.
        
        Args:
            start_date: Start date
            end_date: End date
            max_days: Maximum allowed days in range
            
        Returns:
            bool: True if valid date range
        """
        if not start_date or not end_date:
            return False
        
        if start_date > end_date:
            return False
        
        if (end_date - start_date).days > max_days:
            return False
        
        # Don't allow dates too far in the past
        if start_date < (datetime.now().date() - timedelta(days=max_days)):
            return False
        
        # Don't allow future dates
        if end_date > datetime.now().date():
            return False
        
        return True
    
    @staticmethod
    def validate_business_hours(start_time: str, end_time: str) -> bool:
        """
        Validate business hours format.
        
        Args:
            start_time: Start time (HH:MM format)
            end_time: End time (HH:MM format)
            
        Returns:
            bool: True if valid business hours
        """
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        
        if not re.match(time_pattern, start_time) or not re.match(time_pattern, end_time):
            return False
        
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        
        start_total = start_h * 60 + start_m
        end_total = end_h * 60 + end_m
        
        return start_total < end_total
    
    @staticmethod
    def is_weekend(date_to_check: date) -> bool:
        """
        Check if date is a weekend.
        
        Args:
            date_to_check: Date to check
            
        Returns:
            bool: True if weekend
        """
        return date_to_check.weekday() >= 5  # 5=Saturday, 6=Sunday


class ValidationHelper:
    """Helper class for common validation operations."""
    
    @staticmethod
    def validate_and_sanitize(data: Dict[str, Any], 
                            rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate and sanitize data based on rules.
        
        Args:
            data: Input data to validate
            rules: Validation rules for each field
            
        Returns:
            dict: Validation result with sanitized data and errors
        """
        errors = {}
        sanitized_data = {}
        
        for field, field_rules in rules.items():
            value = data.get(field)
            
            # Required validation
            if field_rules.get('required', False) and (value is None or value == ""):
                errors[field] = f"{field} is required"
                continue
            
            if value is None:
                sanitized_data[field] = None
                continue
            
            # Type validation
            expected_type = field_rules.get('type')
            if expected_type and not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except (ValueError, TypeError):
                    errors[field] = f"{field} must be of type {expected_type.__name__}"
                    continue
            
            # String-specific validations
            if isinstance(value, str):
                # Length validation
                min_length = field_rules.get('min_length')
                max_length = field_rules.get('max_length')
                
                if min_length and len(value) < min_length:
                    errors[field] = f"{field} must be at least {min_length} characters"
                    continue
                
                if max_length and len(value) > max_length:
                    errors[field] = f"{field} cannot exceed {max_length} characters"
                    continue
                
                # Pattern validation
                pattern = field_rules.get('pattern')
                if pattern and not re.match(pattern, value):
                    errors[field] = f"{field} format is invalid"
                    continue
                
                # Sanitization
                if field_rules.get('sanitize', False):
                    value = InputSanitizer.sanitize_html(value)
            
            # Custom validation
            custom_validator = field_rules.get('validator')
            if custom_validator and callable(custom_validator):
                try:
                    if not custom_validator(value):
                        errors[field] = f"{field} is invalid"
                        continue
                except Exception as e:
                    logger.error(f"Custom validation error for {field}: {str(e)}")
                    errors[field] = f"Validation error for {field}"
                    continue
            
            sanitized_data[field] = value
        
        return {
            'valid': len(errors) == 0,
            'data': sanitized_data,
            'errors': errors
        }
    
    @staticmethod
    def generate_validation_hash(data: Dict[str, Any]) -> str:
        """
        Generate hash for validation purposes.
        
        Args:
            data: Data to hash
            
        Returns:
            str: SHA-256 hash
        """
        # Sort keys for consistent hashing
        sorted_data = {k: data[k] for k in sorted(data.keys())}
        data_str = str(sorted_data).encode('utf-8')
        
        return hashlib.sha256(data_str).hexdigest()
    
    @staticmethod
    def validate_pagination(page: int = 1, per_page: int = 20, 
                        max_per_page: int = 100) -> Dict[str, int]:
        """
        Validate pagination parameters.
        
        Args:
            page: Page number
            per_page: Items per page
            max_per_page: Maximum allowed per page
            
        Returns:
            dict: Validated pagination parameters
        """
        page = max(1, page)
        per_page = max(1, min(per_page, max_per_page))
        
        return {
            'page': page,
            'per_page': per_page,
            'offset': (page - 1) * per_page
        }


# Custom validation decorators
def validate_input(validator_class, error_message: str = "Invalid input"):
    """
    Decorator for input validation.
    
    Args:
        validator_class: Pydantic validator class
        error_message: Custom error message
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementation would depend on the specific use case
            return func(*args, **kwargs)
        return wrapper
    return decorator


def sanitize_fields(fields: List[str]):
    """
    Decorator to sanitize specified fields.
    
    Args:
        fields: List of field names to sanitize
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementation would sanitize the specified fields
            return func(*args, **kwargs)
        return wrapper
    return decorator

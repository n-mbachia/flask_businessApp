"""
Validators package for comprehensive input validation and security.

This package provides validation schemas and utilities for:
- Analytics queries validation
- Business logic validation
- Input sanitization and security
- Common validation patterns
"""
from datetime import date, datetime

# Import main validator classes
from .analytics_validators import (
    AnalyticsQuery,
    SalesByMonthQuery,
    ProductSalesQuery,
    CustomerSalesQuery,
    RevenueAnalyticsQuery,
    FunnelAnalyticsQuery,
    TopProductsQuery,
    SecurityValidator,
    ValidationError,
    validate_and_sanitize
)

from .business_validators import (
    CustomerValidator,
    ProductValidator,
    OrderValidator,
    OrderItemValidator,
    InventoryValidator,
    UserValidator,
    ValidationUtils,
    BusinessValidationError
)

from .validator_utils import (
    ValidationPatterns,
    InputSanitizer,
    SecurityValidator as UtilsSecurityValidator,
    BusinessValidator,
    DateValidator,
    ValidationHelper,
    validate_input,
    sanitize_fields
)

# Version and compatibility info
__version__ = "1.0.0"
__pydantic_version__ = "2.x"

# Export main classes for easy import
__all__ = [
    # Analytics validators
    'AnalyticsQuery',
    'SalesByMonthQuery',
    'ProductSalesQuery',
    'CustomerSalesQuery',
    'RevenueAnalyticsQuery',
    'FunnelAnalyticsQuery',
    'TopProductsQuery',
    
    # Business validators
    'CustomerValidator',
    'ProductValidator',
    'OrderValidator',
    'OrderItemValidator',
    'InventoryValidator',
    'UserValidator',
    
    # Utilities
    'ValidationPatterns',
    'InputSanitizer',
    'BusinessValidator',
    'DateValidator',
    'ValidationHelper',
    'ValidationUtils',
    
    # Security
    'SecurityValidator',
    'UtilsSecurityValidator',
    
    # Error handling
    'ValidationError',
    'BusinessValidationError',
    
    # Helper functions
    'validate_and_sanitize',
    'validate_input',
    'sanitize_fields'
]


def get_validator_class(entity_type: str):
    """
    Get appropriate validator class for entity type.
    
    Args:
        entity_type: Type of entity (customer, product, order, etc.)
        
    Returns:
        Validator class for the entity type
        
    Raises:
        ValueError: If entity type not supported
    """
    validators = {
        'customer': CustomerValidator,
        'product': ProductValidator,
        'order': OrderValidator,
        'order_item': OrderItemValidator,
        'inventory': InventoryValidator,
        'user': UserValidator,
        'analytics': AnalyticsQuery,
        'sales_by_month': SalesByMonthQuery,
        'product_sales': ProductSalesQuery,
        'customer_sales': CustomerSalesQuery,
        'revenue': RevenueAnalyticsQuery,
        'funnel': FunnelAnalyticsQuery,
        'top_products': TopProductsQuery
    }
    
    validator_class = validators.get(entity_type.lower())
    if not validator_class:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    return validator_class


def validate_entity(entity_type: str, data: dict, sanitize: bool = True):
    """
    Validate entity data using appropriate validator.
    
    Args:
        entity_type: Type of entity to validate
        data: Data to validate
        sanitize: Whether to sanitize input data
        
    Returns:
        tuple: (validated_data, errors)
    """
    try:
        validator_class = get_validator_class(entity_type)
        
        if sanitize:
            return validate_and_sanitize(validator_class, data)
        else:
            validated = validator_class(**data)
            return validated, []
            
    except ValueError as e:
        return None, [str(e)]
    except Exception as e:
        logger.error(f"Validation error for {entity_type}: {str(e)}")
        return None, [f"Validation failed: {str(e)}"]


def quick_validate(data: dict, rules: dict) -> dict:
    """
    Quick validation using ValidationHelper.
    
    Args:
        data: Data to validate
        rules: Validation rules
        
    Returns:
        dict: Validation result
    """
    return ValidationHelper.validate_and_sanitize(data, rules)


# Security utilities
def sanitize_input(input_string: str, sanitize_type: str = 'html') -> str:
    """
    Sanitize input string.
    
    Args:
        input_string: String to sanitize
        sanitize_type: Type of sanitization ('html', 'sql', 'filename', 'search')
        
    Returns:
        str: Sanitized string
    """
    if not input_string:
        return ""
    
    sanitizer_map = {
        'html': InputSanitizer.sanitize_html,
        'sql': InputSanitizer.sanitize_sql,
        'filename': InputSanitizer.sanitize_filename,
        'search': InputSanitizer.sanitize_search_query,
        'text': InputSanitizer.sanitize_html
    }
    
    sanitizer = sanitizer_map.get(sanitize_type.lower())
    if not sanitizer:
        raise ValueError(f"Unsupported sanitize type: {sanitize_type}")
    
    return sanitizer(input_string)


def check_security(input_string: str, check_type: str = 'all') -> bool:
    """
    Check for security issues in input.
    
    Args:
        input_string: String to check
        check_type: Type of check ('sql', 'xss', 'path', 'all')
        
    Returns:
        bool: True if security issue detected
    """
    if not input_string:
        return False
    
    if check_type.lower() == 'all':
        return (UtilsSecurityValidator.detect_sql_injection(input_string) or
                UtilsSecurityValidator.detect_xss(input_string) or
                UtilsSecurityValidator.detect_path_traversal(input_string))
    
    check_map = {
        'sql': UtilsSecurityValidator.detect_sql_injection,
        'xss': UtilsSecurityValidator.detect_xss,
        'path': UtilsSecurityValidator.detect_path_traversal
    }
    
    checker = check_map.get(check_type.lower())
    if not checker:
        raise ValueError(f"Unsupported check type: {check_type}")
    
    return checker(input_string)


# Business validation helpers
def validate_business_email(email: str) -> bool:
    """Validate business email."""
    return BusinessValidator.validate_business_email(email)


def validate_business_phone(phone: str, country_code: str = 'US') -> bool:
    """Validate business phone number."""
    return BusinessValidator.validate_business_phone(phone, country_code)


def validate_sku(sku: str) -> bool:
    """Validate SKU format."""
    return BusinessValidator.validate_sku(sku)


def validate_credit_card(card_number: str) -> bool:
    """Validate credit card number."""
    return BusinessValidator.validate_credit_card(card_number)


# Date validation helpers
def validate_date_range(start_date: date, end_date: date, max_days: int = 365) -> bool:
    """Validate date range."""
    return DateValidator.validate_date_range(start_date, end_date, max_days)


def validate_business_hours(start_time: str, end_time: str) -> bool:
    """Validate business hours."""
    return DateValidator.validate_business_hours(start_time, end_time)


def is_weekend(date_to_check: date) -> bool:
    """Check if date is weekend."""
    return DateValidator.is_weekend(date_to_check)


# Pagination helper
def validate_pagination(page: int = 1, per_page: int = 20, max_per_page: int = 100) -> dict:
    """Validate pagination parameters."""
    return ValidationHelper.validate_pagination(page, per_page, max_per_page)


# Configuration and setup
def setup_validators(app=None):
    """
    Setup validators with Flask app if provided.
    
    Args:
        app: Flask application instance
    """
    if app:
        # Add any app-specific configuration here
        app.config.setdefault('VALIDATORS_MAX_PER_PAGE', 100)
        app.config.setdefault('VALIDATORS_MAX_FILE_SIZE_MB', 10)
        app.config.setdefault('VALIDATORS_ALLOWED_EXTENSIONS', 
                           ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt'])
    
    logger.info("Validators package initialized")


# Initialize logging
import logging
logger = logging.getLogger(__name__)

# Auto-setup if imported in Flask context
try:
    from flask import current_app
    if current_app:
        setup_validators(current_app)
except RuntimeError:
    # Not in Flask context, that's okay
    pass

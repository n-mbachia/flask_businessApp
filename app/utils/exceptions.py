"""
Custom exception classes for the application.
Provides specific exception types for better error handling.
"""


class BaseBusinessException(Exception):
    """Base exception for all business logic errors."""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BaseBusinessException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class NotFoundError(BaseBusinessException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource_type: str = None):
        self.resource_type = resource_type
        super().__init__(message, "NOT_FOUND")


class BusinessLogicError(BaseBusinessException):
    """Raised when business rules are violated."""
    
    def __init__(self, message: str, rule_type: str = None):
        self.rule_type = rule_type
        super().__init__(message, "BUSINESS_LOGIC_ERROR")


class PermissionError(BaseBusinessException):
    """Raised when user lacks permission for an action."""
    
    def __init__(self, message: str, required_permission: str = None):
        self.required_permission = required_permission
        super().__init__(message, "PERMISSION_ERROR")


class InventoryError(BaseBusinessException):
    """Raised when inventory-related operations fail."""
    
    def __init__(self, message: str, product_id: int = None):
        self.product_id = product_id
        super().__init__(message, "INVENTORY_ERROR")


class PaymentError(BaseBusinessException):
    """Raised when payment operations fail."""
    
    def __init__(self, message: str, payment_method: str = None):
        self.payment_method = payment_method
        super().__init__(message, "PAYMENT_ERROR")


class ConfigurationError(BaseBusinessException):
    """Raised when system configuration is invalid."""
    
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        super().__init__(message, "CONFIGURATION_ERROR")

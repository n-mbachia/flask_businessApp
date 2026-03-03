"""
Business logic validation schemas for core business operations.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator, Field, ConfigDict
import re
import logging

logger = logging.getLogger(__name__)


class CustomerValidator(BaseModel):
    """Validation for customer data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=100, 
                       description="Customer name is required")
    email: str = Field(..., min_length=5, max_length=120, 
                        description="Valid email address required")
    phone: Optional[str] = Field(None, max_length=20, 
                               description="Phone number (optional)")
    address: Optional[str] = Field(None, max_length=500, 
                                 description="Customer address")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Customer name is required')
        
        # Check for potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
        if any(char in v.lower() for char in dangerous_chars):
            raise ValueError('Customer name contains invalid characters')
        
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v:
            raise ValueError('Email is required')
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        
        return v.lower().strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return None
        
        # Remove common formatting
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Check if it's a reasonable phone number
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Invalid phone number format')
        
        return v.strip()

class ProductValidator(BaseModel):
    """Validation for product data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=200, 
                       description="Product name is required")
    description: Optional[str] = Field(None, max_length=2000, 
                                     description="Product description")
    price: float = Field(..., gt=0, le=999999.99, 
                         description="Product price must be positive")
    cost_price: Optional[float] = Field(None, ge=0, le=999999.99, 
                                      description="Cost price for profit calculation")
    category: Optional[str] = Field(None, max_length=100, 
                                    description="Product category")
    sku: Optional[str] = Field(None, max_length=50, 
                               description="Stock keeping unit")
    barcode: Optional[str] = Field(None, max_length=50,
                                    description="Barcode / UPC")
    reorder_point: int = Field(0, ge=0, le=999999, 
                              description="Reorder point")
    initial_quantity: int = Field(0, ge=0, le=999999,
                                   description="Initial stock quantity (only on create)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Product name is required')
        
        # Check for SQL injection patterns
        sql_patterns = ['select', 'insert', 'update', 'delete', 'drop', 'union', '--', ';']
        if any(pattern in v.lower() for pattern in sql_patterns):
            raise ValueError('Invalid product name format')
        
        return v.strip()
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                raise ValueError('Category cannot be empty if provided')
            
            # Check for dangerous patterns
            dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
            if any(pattern in v.lower() for pattern in dangerous_patterns):
                raise ValueError('Invalid category format')
        
        return v
    
    @field_validator('cost_price')
    @classmethod
    def validate_cost_price(cls, v, info):
        if v is not None:
            price = info.data.get('price', 0)
            if v > price:
                raise ValueError('Cost price cannot be greater than selling price')
        
        return v
    
    @field_validator('reorder_point')
    @classmethod
    def validate_reorder_point(cls, v, info):
        if v < 0:
            raise ValueError('Reorder point cannot be negative')
        return v
    
    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, v):
        if v is not None:
            v = v.strip()
            if v == "":
                # Empty string after stripping → treat as no value
                return None
            # Optional: add format validation for non-empty barcodes (e.g., check length, digits)
            # if not v.isdigit() or len(v) not in [8,12,13]:
            #     raise ValueError('Invalid barcode format')
        return v


class OrderValidator(BaseModel):
    """Validation for order data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    customer_id: int = Field(..., gt=0, description="Valid customer ID required")
    order_date: Optional[date] = Field(None, description="Order date")
    status: str = Field('pending', 
                        description="Order status: pending, confirmed, shipped, delivered, cancelled")
    notes: Optional[str] = Field(None, max_length=2000, 
                                description="Order notes")
    
    @field_validator('customer_id')
    @classmethod
    def validate_customer_id(cls, v):
        if v <= 0:
            raise ValueError('Valid customer ID required')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        if v.lower() not in allowed_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(allowed_statuses)}')
        return v.lower()
    
    @field_validator('order_date')
    @classmethod
    def validate_order_date(cls, v):
        if v and v > datetime.now().date():
            raise ValueError('Order date cannot be in the future')
        
        # Don't allow orders older than 5 years
        if v and (datetime.now().date() - v).days > 1825:  # 5 years
            raise ValueError('Order date cannot be more than 5 years old')
        
        return v


class OrderItemValidator(BaseModel):
    """Validation for order item data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    product_id: int = Field(..., gt=0, description="Valid product ID required")
    quantity: int = Field(..., gt=0, le=10000, 
                       description="Quantity must be positive")
    unit_price: float = Field(..., gt=0, le=999999.99, 
                           description="Unit price must be positive")
    discount: Optional[float] = Field(0, ge=0, le=100, 
                                    description="Discount percentage (0-100)")
    
    @field_validator('product_id')
    @classmethod
    def validate_product_id(cls, v):
        if v <= 0:
            raise ValueError('Valid product ID required')
        return v
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        
        # Reasonable quantity limits
        if v > 10000:
            raise ValueError('Quantity exceeds maximum allowed')
        
        return v
    
    @field_validator('unit_price')
    @classmethod
    def validate_unit_price(cls, v):
        if v <= 0:
            raise ValueError('Unit price must be positive')
        
        # Reasonable price limits
        if v > 999999.99:
            raise ValueError('Unit price exceeds maximum allowed')
        
        return v
    
    @field_validator('discount')
    @classmethod
    def validate_discount(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Discount must be between 0 and 100')
        return v


class InventoryValidator(BaseModel):
    """Validation for inventory operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    product_id: int = Field(..., gt=0, description="Valid product ID required")
    quantity_change: int = Field(..., 
                             description="Quantity change (positive for addition, negative for removal)")
    reason: Optional[str] = Field(None, max_length=500, 
                                 description="Reason for inventory change")
    new_quantity: Optional[int] = Field(None, ge=0, 
                                      description="New total quantity")
    
    @field_validator('product_id')
    @classmethod
    def validate_product_id(cls, v):
        if v <= 0:
            raise ValueError('Valid product ID required')
        return v
    
    @field_validator('quantity_change')
    @classmethod
    def validate_quantity_change(cls, v):
        if v == 0:
            raise ValueError('Quantity change cannot be zero')
        
        # Reasonable limits for single adjustment
        if abs(v) > 10000:
            raise ValueError('Quantity change exceeds maximum allowed')
        
        return v
    
    @field_validator('new_quantity')
    @classmethod
    def validate_new_quantity(cls, v):
        if v is not None and v < 0:
            raise ValueError('New quantity cannot be negative')
        return v


class UserValidator(BaseModel):
    """Validation for user data."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    username: str = Field(..., min_length=3, max_length=50, 
                          description="Username (3-50 characters)")
    email: str = Field(..., min_length=5, max_length=120, 
                        description="Valid email address")
    password: Optional[str] = Field(None, min_length=8, max_length=128, 
                                   description="Strong password required")
    role: str = Field('user', 
                      description="User role: admin, manager, user")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Username is required')
        
        v = v.strip()
        
        # Username format validation
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        
        if len(v) > 50:
            raise ValueError('Username cannot exceed 50 characters')
        
        # Allowed characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        
        # Reserved usernames
        reserved = ['admin', 'root', 'system', 'api', 'www', 'mail', 'support']
        if v.lower() in reserved:
            raise ValueError('Username is reserved')
        
        return v.lower()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v:
            raise ValueError('Email is required')
        
        v = v.strip().lower()
        
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return None  # Password optional for updates
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        if len(v) > 128:
            raise ValueError('Password cannot exceed 128 characters')
        
        # Password strength requirements
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*(),.?":{}|<>' for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numbers')
        
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['admin', 'manager', 'user']
        if v.lower() not in allowed_roles:
            raise ValueError(f'Invalid role. Must be one of: {", ".join(allowed_roles)}')
        return v.lower()


# Validation utilities
class ValidationUtils:
    """Utility functions for validation operations."""
    
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
        errors = {}
        
        if page < 1:
            errors['page'] = 'Page must be at least 1'
        
        if per_page < 1:
            errors['per_page'] = 'Per page must be at least 1'
        elif per_page > max_per_page:
            errors['per_page'] = f'Per page cannot exceed {max_per_page}'
        
        if errors:
            raise ValueError(f"Pagination validation failed: {errors}")
        
        return {
            'page': page,
            'per_page': per_page,
            'offset': (page - 1) * per_page
        }
    
    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search query to prevent injection.
        
        Args:
            query: Raw search query
            
        Returns:
            str: Sanitized search query
        """
        if not query:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '--', '/*', '*/']
        sanitized = query
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_file_upload(file_data: Dict[str, Any], 
                          allowed_extensions: List[str] = None,
                          max_size_mb: int = 10) -> Dict[str, Any]:
        """
        Validate file upload parameters.
        
        Args:
            file_data: File data dictionary
            allowed_extensions: List of allowed file extensions
            max_size_mb: Maximum file size in MB
            
        Returns:
            dict: Validation result
        """
        errors = []
        
        filename = file_data.get('filename', '')
        file_size = file_data.get('size', 0)
        content_type = file_data.get('content_type', '')
        
        # Validate filename
        if not filename:
            errors.append('Filename is required')
        else:
            # Check for dangerous filenames
            dangerous_names = ['..', '/', '\\', 'con', 'prn', 'aux', 'nul']
            if any(name in filename.lower() for name in dangerous_names):
                errors.append('Invalid filename')
        
        # Validate file extension
        if allowed_extensions:
            file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
            if file_ext not in allowed_extensions:
                errors.append(f'File extension .{file_ext} not allowed')
        
        # Validate file size
        if file_size > max_size_mb * 1024 * 1024:
            errors.append(f'File size exceeds {max_size_mb}MB limit')
        
        # Validate content type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                        'text/plain', 'application/msword']
        if content_type not in allowed_types:
            errors.append('Invalid file type')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'sanitized_filename': ValidationUtils.sanitize_filename(filename)
        }
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for secure storage."""
        if not filename:
            return "unnamed_file"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        sanitized = ''.join(c for c in filename if c not in dangerous_chars)
        
        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        
        return sanitized.strip()


# Custom validation exceptions
class BusinessValidationError(Exception):
    """Custom exception for business validation errors."""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        result = {
            'error': 'business_validation_error',
            'message': self.message
        }
        
        if self.field:
            result['field'] = self.field
        
        if self.code:
            result['code'] = self.code
        
        return result

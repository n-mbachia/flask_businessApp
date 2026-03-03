"""
Analytics validation schemas using Pydantic v2 for robust input validation.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, field_validator, Field, ConfigDict
import re
import logging

logger = logging.getLogger(__name__)


class AnalyticsQuery(BaseModel):
    """Base validation for analytics queries."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    user_id: int = Field(..., gt=0, description="User ID must be positive")
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('End date must be after start date')
        return v
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('User ID must be positive')
        return v


class SalesByMonthQuery(AnalyticsQuery):
    """Validation for monthly sales queries."""
    year: Optional[int] = Field(None, ge=2020, le=datetime.now().year, 
                             description="Year must be between 2020 and current year")
    month: Optional[int] = Field(None, ge=1, le=12, 
                              description="Month must be between 1 and 12")
    limit: int = Field(12, ge=1, le=100, 
                      description="Limit must be between 1 and 100")
    
    @field_validator('month')
    @classmethod
    def validate_month_with_year(cls, v, info):
        if v and 'year' not in info.data:
            raise ValueError('Year must be specified when month is provided')
        return v
    
    @field_validator('year', 'month')
    @classmethod
    def validate_date_not_future(cls, v):
        current_date = datetime.now()
        if isinstance(v, int):
            if 'year' in str(v).lower():
                if v > current_date.year:
                    raise ValueError('Year cannot be in the future')
            elif 'month' in str(v).lower():
                if v > 12:
                    raise ValueError('Invalid month')
        return v


class ProductSalesQuery(AnalyticsQuery):
    """Validation for product sales queries."""
    product_id: Optional[int] = Field(None, gt=0, description="Product ID must be positive")
    limit: Optional[int] = Field(None, ge=1, le=100, 
                                description="Limit must be between 1 and 100")
    sort_by: str = Field('revenue', 
                        description="Sort by column: revenue, units, profit, name")
    sort_order: str = Field('desc', 
                          description="Sort order: asc, desc")
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        allowed = ['revenue', 'units', 'profit', 'name']
        if v.lower() not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        allowed = ['asc', 'desc']
        if v.lower() not in allowed:
            raise ValueError(f'sort_order must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @field_validator('product_id')
    @classmethod
    def validate_product_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Product ID must be positive')
        return v


class CustomerSalesQuery(AnalyticsQuery):
    """Validation for customer sales queries."""
    customer_id: Optional[int] = Field(None, gt=0, description="Customer ID must be positive")
    limit: Optional[int] = Field(None, ge=1, le=100, 
                                description="Limit must be between 1 and 100")
    sort_by: str = Field('spent', 
                        description="Sort by column: spent, orders, products, name, recent")
    sort_order: str = Field('desc', 
                          description="Sort order: asc, desc")
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        allowed = ['spent', 'orders', 'products', 'name', 'recent']
        if v.lower() not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        allowed = ['asc', 'desc']
        if v.lower() not in allowed:
            raise ValueError(f'sort_order must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @field_validator('customer_id')
    @classmethod
    def validate_customer_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Customer ID must be positive')
        return v


class RevenueAnalyticsQuery(AnalyticsQuery):
    """Validation for revenue analytics queries."""
    group_by: str = Field('day', 
                         description="Group by period: day, week, month")
    limit: Optional[int] = Field(None, ge=1, le=365, 
                                description="Limit must be between 1 and 365")
    
    @field_validator('group_by')
    @classmethod
    def validate_group_by(cls, v):
        allowed = ['day', 'week', 'month']
        if v.lower() not in allowed:
            raise ValueError(f'group_by must be one of: {", ".join(allowed)}')
        return v.lower()


class FunnelAnalyticsQuery(AnalyticsQuery):
    """Validation for sales funnel queries."""
    include_abandoned: bool = Field(True, description="Include abandoned carts")
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date_not_too_old(cls, v):
        if v and (datetime.now().date() - v).days > 365:
            raise ValueError('Start date cannot be more than 1 year old')
        return v


class TopProductsQuery(AnalyticsQuery):
    """Validation for top products queries."""
    limit: int = Field(10, ge=1, le=50, 
                      description="Limit must be between 1 and 50")
    category: Optional[str] = Field(None, description="Filter by product category")
    min_units_sold: int = Field(0, ge=0, 
                               description="Minimum units sold threshold")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                raise ValueError('Category cannot be empty')
            # Check for SQL injection patterns
            sql_patterns = ['select', 'insert', 'update', 'delete', 'drop', 'union', '--', ';']
            if any(pattern in v.lower() for pattern in sql_patterns):
                raise ValueError('Invalid category format')
        return v
    
    @field_validator('min_units_sold')
    @classmethod
    def validate_min_units(cls, v):
        if v < 0:
            raise ValueError('Minimum units sold cannot be negative')
        return v


# Custom validators for common patterns
class SecurityValidator:
    """Security-focused validators for common attack patterns."""
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input to prevent XSS and injection."""
        if not value:
            return ""
        
        # Remove potential XSS patterns
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
        ]
        
        sanitized = value
        for pattern in xss_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove SQL injection patterns
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter|exec)',
            r'(--|#|\/\*|\*\/)',
            r'(\bOR\b.*\b1\s*=\s*1\b)',
            r'(\bAND\b.*\b1\s*=\s*1\b)',
        ]
        
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @staticmethod
    def validate_no_sql_injection(value: str) -> str:
        """Validate that string doesn't contain SQL injection patterns."""
        if not value:
            return value
        
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter|exec)',
            r'(--|#|\/\*|\*\/)',
            r'(\bOR\b.*\b1\s*=\s*1\b)',
            r'(\bAND\b.*\b1\s*=\s*1\b)',
            r'(\'.*(OR|AND).*\'.*\=.*\')',
            r'(\'.*\=.*\'.*(OR|AND).*)',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError('Potential SQL injection detected')
        
        return value
    
    @staticmethod
    def validate_no_xss(value: str) -> str:
        """Validate that string doesn't contain XSS patterns."""
        if not value:
            return value
        
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError('Potential XSS attack detected')
        
        return value


# Error handling utilities
class ValidationError(Exception):
    """Custom validation error with additional context."""
    def __init__(self, message: str, field: str = None, value: any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for API responses."""
        result = {'message': self.message}
        if self.field:
            result['field'] = self.field
        if self.value is not None:
            result['value'] = str(self.value)
        return result


def validate_and_sanitize(validator_class, data: dict) -> tuple[any, list]:
    """
    Validate data using a validator class and return sanitized data with errors.
    
    Args:
        validator_class: Pydantic validator class
        data: Input data to validate
        
    Returns:
        tuple: (validated_data, errors)
    """
    errors = []
    
    try:
        # Sanitize string fields first
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = SecurityValidator.sanitize_string(value)
            else:
                sanitized_data[key] = value
        
        # Validate with Pydantic
        validated = validator_class(**sanitized_data)
        return validated, errors
        
    except ValueError as e:
        errors.append(ValidationError(str(e)))
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        errors.append(ValidationError("Validation failed"))
    
    return None, errors

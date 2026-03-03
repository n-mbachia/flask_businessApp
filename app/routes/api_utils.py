"""
API utilities for standardized response formatting and documentation.
"""
from flask import jsonify, request, Response
from typing import Dict, Any, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class APIResponse:
    """Standardized API response formatting."""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", 
                status_code: int = 200, meta: Dict[str, Any] = None) -> Response:
        """
        Create a successful API response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            meta: Additional metadata
            
        Returns:
            Flask Response object
        """
        response = {
            'status': 'success',
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        if meta:
            response['meta'] = meta
            
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str, status_code: int = 400, 
               error_code: str = None, details: Dict[str, Any] = None) -> Response:
        """
        Create an error API response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            details: Additional error details
            
        Returns:
            Flask Response object
        """
        response = {
            'status': 'error',
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if error_code:
            response['error_code'] = error_code
            
        if details:
            response['details'] = details
            
        return jsonify(response), status_code
    
    @staticmethod
    def validation_errors(errors: Dict[str, Any], 
                            message: str = "Validation failed") -> Response:
        """
        Create a validation error response.
        
        Args:
            errors: Validation errors dictionary
            message: Error message
            
        Returns:
            Flask Response object
        """
        return APIResponse.error(
            message=message,
            status_code=422,
            error_code='VALIDATION_ERROR',
            details={'validation_errors': errors}
        )
    
    @staticmethod
    def paginated(data: list, total: int, page: int, per_page: int,
                   message: str = "Data retrieved successfully") -> Response:
        """
        Create a paginated API response.
        
        Args:
            data: List of items
            total: Total number of items
            page: Current page number
            per_page: Items per page
            message: Success message
            
        Returns:
            Flask Response object
        """
        total_pages = (total + per_page - 1) // per_page
        
        meta = {
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_items': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        return APIResponse.success(
            data=data,
            message=message,
            meta=meta
        )
    
    @staticmethod
    def created(data: Any = None, message: str = "Resource created successfully") -> Response:
        """Create a resource created response."""
        return APIResponse.success(
            data=data,
            message=message,
            status_code=201
        )
    
    @staticmethod
    def updated(data: Any = None, message: str = "Resource updated successfully") -> Response:
        """Create a resource updated response."""
        return APIResponse.success(
            data=data,
            message=message,
            status_code=200
        )
    
    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> Response:
        """Create a resource deleted response."""
        return APIResponse.success(
            data=None,
            message=message,
            status_code=204
        )


class APIValidator:
    """API request validation utilities."""
    
    @staticmethod
    def validate_json() -> bool:
        """Validate that request contains JSON data."""
        return request.is_json
    
    @staticmethod
    def validate_content_type(allowed_types: list) -> bool:
        """Validate request content type."""
        return request.content_type in allowed_types
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], 
                             required_fields: list) -> Dict[str, str]:
        """
        Validate required fields in request data.
        
        Args:
            data: Request data dictionary
            required_fields: List of required field names
            
        Returns:
            Dictionary of missing fields and their error messages
        """
        errors = {}
        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = f"{field} is required"
        return errors
    
    @staticmethod
    def validate_field_types(data: Dict[str, Any], 
                          field_types: Dict[str, type]) -> Dict[str, str]:
        """
        Validate field types in request data.
        
        Args:
            data: Request data dictionary
            field_types: Dictionary mapping field names to expected types
            
        Returns:
            Dictionary of type validation errors
        """
        errors = {}
        for field, expected_type in field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                errors[field] = f"{field} must be of type {expected_type.__name__}"
        return errors
    
    @staticmethod
    def validate_field_lengths(data: Dict[str, Any], 
                          field_lengths: Dict[str, int]) -> Dict[str, str]:
        """
        Validate field lengths in request data.
        
        Args:
            data: Request data dictionary
            field_lengths: Dictionary mapping field names to max lengths
            
        Returns:
            Dictionary of length validation errors
        """
        errors = {}
        for field, max_length in field_lengths.items():
            if field in data and isinstance(data[field], str):
                if len(data[field]) > max_length:
                    errors[field] = f"{field} cannot exceed {max_length} characters"
        return errors


class APIDocumentation:
    """API documentation utilities."""
    
    @staticmethod
    def generate_endpoint_docs(endpoint_name: str, methods: list,
                           description: str, parameters: list = None,
                           responses: dict = None) -> dict:
        """
        Generate documentation for an API endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
            methods: HTTP methods supported
            description: Endpoint description
            parameters: List of parameters
            responses: Dictionary of possible responses
            
        Returns:
            Documentation dictionary
        """
        return {
            'endpoint': endpoint_name,
            'methods': methods,
            'description': description,
            'parameters': parameters or [],
            'responses': responses or {
                '200': {'description': 'Success'},
                '400': {'description': 'Bad Request'},
                '401': {'description': 'Unauthorized'},
                '403': {'description': 'Forbidden'},
                '404': {'description': 'Not Found'},
                '422': {'description': 'Validation Error'},
                '500': {'description': 'Internal Server Error'}
            }
        }
    
    @staticmethod
    def generate_parameter_docs(name: str, type_: str, required: bool = False,
                             description: str = "", example: Any = None) -> dict:
        """
        Generate documentation for a parameter.
        
        Args:
            name: Parameter name
            type_: Parameter type
            required: Whether parameter is required
            description: Parameter description
            example: Example value
            
        Returns:
            Parameter documentation dictionary
        """
        param_doc = {
            'name': name,
            'type': type_,
            'required': required,
            'description': description
        }
        
        if example is not None:
            param_doc['example'] = example
            
        return param_doc


class APIHeaders:
    """API response headers utilities."""
    
    @staticmethod
    def add_cors_headers(response: Response) -> Response:
        """Add CORS headers to response."""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
    
    @staticmethod
    def add_security_headers(response: Response) -> Response:
        """Add security headers to response."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    @staticmethod
    def add_cache_headers(response: Response, cache_control: str = 'no-cache') -> Response:
        """Add cache control headers to response."""
        response.headers['Cache-Control'] = cache_control
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response


class APIRateLimiting:
    """API rate limiting utilities."""
    
    @staticmethod
    def add_rate_limit_headers(response: Response, limit: int, 
                           remaining: int, reset_time: int) -> Response:
        """
        Add rate limiting headers to response.
        
        Args:
            response: Flask response object
            limit: Request limit
            remaining: Remaining requests
            reset_time: Unix timestamp when limit resets
            
        Returns:
            Response with rate limit headers
        """
        response.headers['X-RateLimit-Limit'] = str(limit)
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(reset_time)
        return response
    
    @staticmethod
    def rate_limit_exceeded(limit: int, reset_time: int) -> Response:
        """
        Create a rate limit exceeded response.
        
        Args:
            limit: Request limit
            reset_time: Unix timestamp when limit resets
            
        Returns:
            Rate limit exceeded response
        """
        response = APIResponse.error(
            message="Rate limit exceeded",
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details={
                'limit': limit,
                'reset_time': reset_time,
                'retry_after': reset_time
            }
        )
        
        # Add retry-after header
        response.headers['Retry-After'] = str(reset_time)
        return response


class APIVersioning:
    """API versioning utilities."""
    
    @staticmethod
    def add_version_header(response: Response, version: str = "v1") -> Response:
        """Add API version header to response."""
        response.headers['API-Version'] = version
        return response
    
    @staticmethod
    def get_version_from_request() -> str:
        """Get API version from request headers."""
        return request.headers.get('API-Version', 'v1')
    
    @staticmethod
    def validate_version(supported_versions: list = None) -> bool:
        """
        Validate requested API version.
        
        Args:
            supported_versions: List of supported versions
            
        Returns:
            True if version is supported
        """
        if supported_versions is None:
            supported_versions = ['v1']
            
        requested_version = APIVersioning.get_version_from_request()
        return requested_version in supported_versions


def handle_api_errors(func):
    """
    Decorator for consistent API error handling.
    
    Args:
        func: API function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"API validation error: {str(e)}")
            return APIResponse.validation_errors({'error': str(e)})
        except KeyError as e:
            logger.error(f"API missing field error: {str(e)}")
            return APIResponse.error(
                message=f"Missing required field: {str(e)}",
                status_code=400,
                error_code='MISSING_FIELD'
            )
        except Exception as e:
            logger.error(f"API internal error: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Internal server error",
                status_code=500,
                error_code='INTERNAL_ERROR'
            )
    
    return wrapper


def validate_api_request(required_fields: list = None, 
                    field_types: dict = None,
                    field_lengths: dict = None):
    """
    Decorator for API request validation.
    
    Args:
        required_fields: List of required field names
        field_types: Dictionary mapping field names to expected types
        field_lengths: Dictionary mapping field names to max lengths
        
    Returns:
        Wrapped function with validation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate JSON content type
            if not APIValidator.validate_json():
                return APIResponse.error(
                    message="Content-Type must be application/json",
                    status_code=400,
                    error_code='INVALID_CONTENT_TYPE'
                )
            
            # Get request data
            try:
                data = request.get_json()
            except Exception as e:
                logger.error(f"JSON parsing error: {str(e)}")
                return APIResponse.error(
                    message="Invalid JSON format",
                    status_code=400,
                    error_code='INVALID_JSON'
                )
            
            if data is None:
                data = {}
            
            # Validate required fields
            errors = {}
            if required_fields:
                required_errors = APIValidator.validate_required_fields(data, required_fields)
                errors.update(required_errors)
            
            # Validate field types
            if field_types:
                type_errors = APIValidator.validate_field_types(data, field_types)
                errors.update(type_errors)
            
            # Validate field lengths
            if field_lengths:
                length_errors = APIValidator.validate_field_lengths(data, field_lengths)
                errors.update(length_errors)
            
            if errors:
                return APIResponse.validation_errors(errors)
            
            # Add validated data to kwargs
            kwargs['validated_data'] = data
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Standard error codes
class APIErrorCodes:
    """Standard API error codes."""
    
    # Validation errors
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    MISSING_FIELD = 'MISSING_FIELD'
    INVALID_FIELD_TYPE = 'INVALID_FIELD_TYPE'
    FIELD_TOO_LONG = 'FIELD_TOO_LONG'
    
    # Authentication errors
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    TOKEN_INVALID = 'TOKEN_INVALID'
    ACCOUNT_LOCKED = 'ACCOUNT_LOCKED'
    
    # Authorization errors
    UNAUTHORIZED = 'UNAUTHORIZED'
    FORBIDDEN = 'FORBIDDEN'
    RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND'
    
    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    
    # System errors
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
    INVALID_CONTENT_TYPE = 'INVALID_CONTENT_TYPE'
    INVALID_JSON = 'INVALID_JSON'
    
    # Business logic errors
    DUPLICATE_RESOURCE = 'DUPLICATE_RESOURCE'
    INVALID_OPERATION = 'INVALID_OPERATION'
    RESOURCE_LIMIT_EXCEEDED = 'RESOURCE_LIMIT_EXCEEDED'


# Standard response messages
class APIMessages:
    """Standard API response messages."""
    
    # Success messages
    SUCCESS = "Operation completed successfully"
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"
    DATA_RETRIEVED = "Data retrieved successfully"
    
    # Error messages
    VALIDATION_FAILED = "Request validation failed"
    INVALID_REQUEST = "Invalid request format"
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN = "Access denied"
    NOT_FOUND = "Resource not found"
    RATE_LIMITED = "Rate limit exceeded"
    SERVER_ERROR = "Internal server error"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"

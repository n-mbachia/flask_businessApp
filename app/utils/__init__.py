"""
Utility functions and helpers for the application.

This package contains various utility modules:
- logging: Logging configuration
- context_processors: Template context processors
- template_filters: Custom Jinja2 template filters
- error_handlers: Error handling and HTTP error pages
- cache: Cache utilities
- decorators: Decorators for views and functions
- helpers: Helper functions for various tasks
- filters: Custom Jinja2 template filters
- csrf_utils: CSRF utility functions
"""

from .logging import configure_logging
from .context_processors import register_context_processors
from .template_filters import register_template_filters
from .error_handlers import register_error_handlers
from .cache import (
    get_cache,
    init_cache, 
    clear_cache, 
    cached,
    invalidate_cache,
    generate_cache_key,
)
from .decorators import (
    track_performance,
    performance_log,
    rate_limit,
    handle_exceptions,
    role_required
)
from .helpers import (
    parse_date,
    get_pagination,
    json_response,
    allowed_file,
    get_file_extension,
    get_week_range,
    get_month_range,
    safe_template_render,
    save_product_image,
    delete_product_image
)
from .db_helpers import reset_db_session, rollback_db_session
from .url_utils import is_safe_url
from .exceptions import (
    ValidationError,
    BusinessLogicError,
    NotFoundError,
    PermissionError,
    InventoryError,
    PaymentError,
    ConfigurationError
)

try:
    from .filters import (
        format_currency,
        format_date,
        format_datetime,
        render_safe,
        render_safe_data,
        filter_registry
    )
    _HAS_FILTERS = True
except ImportError as e:
    print(f"Warning: Could not import filters: {e}")
    _HAS_FILTERS = False
from .csrf_utils import (
    get_csrf_token,
    validate_csrf_token,
    csrf_exempt
)

__all__ = [
    # Exceptions
    'ValidationError',
    'BusinessLogicError',
    'NotFoundError',
    'PermissionError',
    'InventoryError',
    'PaymentError',
    'ConfigurationError',
    
    # Cache
    'get_cache',
    'init_cache',
    'clear_cache',
    'cached',
    'invalidate_cache',
    'generate_cache_key',
    
    # Decorators
    'track_performance',
    'performance_log',
    'rate_limit',
    'handle_exceptions',
    'role_required',
    
    # Helpers
    'parse_date',
    'get_pagination',
    'json_response',
    'allowed_file',
    'get_file_extension',
    'get_week_range',
    'get_month_range',
    'safe_template_render',
    'save_product_image',
    'delete_product_image',
    'reset_db_session',
    'rollback_db_session',
    'is_safe_url',
    
    # Filters
    'format_currency',
    'format_date',
    'format_datetime',
    'render_safe',
    'render_safe_data',
    'filter_registry',
    
    # CSRF
    'get_csrf_token',
    'validate_csrf_token',
    'csrf_exempt',
    
    # Utility
    'configure_logging',
    'register_context_processors',
    'register_template_filters',
    'register_error_handlers',
]

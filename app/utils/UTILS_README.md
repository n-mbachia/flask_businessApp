# App Utils Documentation

This directory contains utility functions, helpers, and modules that provide common functionality across the application.

## Directory Structure

```
app/utils/
├── __init__.py              # Main imports and exports
├── cache.py                 # Caching utilities and decorators
├── context_processors.py   # Flask template context processors
├── csrf_utils.py           # CSRF protection utilities
├── decorators.py           # View and function decorators
├── email.py                # Email sending utilities
├── error_handlers.py       # HTTP error handlers
├── exceptions.py           # Custom exception classes
├── filters.py              # Custom Jinja2 template filters
├── helpers.py              # General helper functions
├── logging.py              # Logging configuration
├── static_utils.py         # Static file utilities
├── template_filters.py     # Template filter registration
└── UTILS_README.md         # This documentation
```

## Core Modules

### Cache (`cache.py`)

Provides caching functionality with Redis/Memcached support.

**Key Functions:**
- `get_cache()` - Get cache instance
- `init_cache(app)` - Initialize cache for Flask app
- `clear_cache()` - Clear all cached data
- `@cached(timeout=300)` - Decorator for caching function results
- `invalidate_cache(key_pattern)` - Invalidate cache by pattern
- `generate_cache_key(*args, **kwargs)` - Generate cache keys

**Usage:**
```python
from app.utils import cached

@cached(timeout=600)
def expensive_operation(param):
    # Expensive computation
    return result
```

### Decorators (`decorators.py`)

Provides useful decorators for views and functions.

**Available Decorators:**
- `@performance_log` - Logs function execution time
- `@track_performance(metric_name)` - Tracks performance metrics
- `@rate_limit(max_calls=30, period=60)` - Rate limiting
- `@handle_exceptions` - Graceful exception handling
- `@role_required('admin')` - Role-based access control

**Usage:**
```python
from app.utils import track_performance, rate_limit

@orders_bp.route('/dashboard')
@track_performance('dashboard_load')
@rate_limit(max_calls=30, period=60)
def dashboard():
    return render_template('dashboard.html')
```

### Helpers (`helpers.py`)

General utility functions for common tasks.

**Key Functions:**
- `parse_date(date_string)` - Parse date strings safely
- `get_pagination(query, page, per_page)` - Create pagination objects
- `json_response(data, status=200)` - Create JSON responses
- `allowed_file(filename, allowed_extensions)` - Validate file types
- `get_file_extension(filename)` - Get file extension
- `get_week_range(date)` - Get week start/end dates
- `get_month_range(date)` - Get month start/end dates
- `safe_template_render(template, **context)` - Safe template rendering

**Usage:**
```python
from app.utils import get_pagination, json_response

@orders_bp.route('/api/orders')
def get_orders():
    orders = Order.query.all()
    pagination = get_pagination(orders, page=1, per_page=20)
    return json_response({
        'orders': [order.to_dict() for order in pagination.items]
    })
```

### Exceptions (`exceptions.py`)

Custom exception classes for better error handling.

**Exception Classes:**
- `ValidationError` - Data validation errors
- `BusinessLogicError` - Business rule violations
- `NotFoundError` - Resource not found errors
- `PermissionError` - Access permission errors
- `InventoryError` - Inventory management errors
- `PaymentError` - Payment processing errors
- `ConfigurationError` - Configuration issues

**Usage:**
```python
from app.utils.exceptions import ValidationError, InventoryError

def update_inventory(product_id, quantity):
    if quantity < 0:
        raise ValidationError("Quantity cannot be negative")
    if not enough_stock:
        raise InventoryError("Insufficient stock")
```

### Email (`email.py`)

Email sending utilities with template support.

**Key Functions:**
- `send_email(to, subject, template, **context)` - Send templated email
- `send_order_confirmation(order)` - Send order confirmation
- `send_password_reset(user, token)` - Send password reset email

**Usage:**
```python
from app.utils.email import send_email

send_email(
    to=user.email,
    subject='Order Confirmation',
    template='emails/order_confirmation.html',
    order=order
)
```

### Error Handlers (`error_handlers.py`)

HTTP error handling and custom error pages.

**Features:**
- 404 Not Found handling
- 500 Internal Server Error handling
- 403 Forbidden handling
- JSON error responses for AJAX requests
- Error logging and monitoring

### Context Processors (`context_processors.py`)

Template context processors for global variables.

**Available Processors:**
- `app_config` - Application configuration
- `current_user_data` - Current user information
- `currency_info` - Currency formatting settings

### Template Filters (`template_filters.py` & `filters.py`)

Custom Jinja2 template filters.

**Available Filters:**
- `format_currency` - Currency formatting
- `format_date` - Date formatting
- `format_datetime` - DateTime formatting
- `render_safe` - Safe HTML rendering
- `render_safe_data` - Safe data rendering

**Template Usage:**
```html
{{ order.total_amount|format_currency }}
{{ order.created_at|format_date('%Y-%m-%d') }}
{{ content|render_safe }}
```

### CSRF Utils (`csrf_utils.py`)

CSRF protection utilities.

**Functions:**
- `get_csrf_token()` - Get current CSRF token
- `validate_csrf_token(token)` - Validate CSRF token
- `@csrf_exempt` - Exempt view from CSRF protection

### Static Utils (`static_utils.py`)

Static file management utilities.

**Functions:**
- `get_static_url(filename)` - Get static file URL
- `generate_asset_hash(filepath)` - Generate asset hash for cache busting
- `minify_css(content)` - CSS minification
- `minify_js(content)` - JavaScript minification

### Logging (`logging.py`)

Logging configuration and utilities.

**Functions:**
- `configure_logging(app)` - Configure application logging
- `get_logger(name)` - Get configured logger

## Import Patterns

### Recommended Imports

```python
# Core utilities
from app.utils import (
    ValidationError, BusinessLogicError,
    cached, track_performance, rate_limit,
    get_pagination, json_response,
    format_currency, parse_date
)

# Specific modules
from app.utils.email import send_email
from app.utils.exceptions import InventoryError
from app.utils.decorators import handle_exceptions
```

### Available from `__init__.py`

All commonly used functions and classes are exported from `app.utils.__init__.py`:

```python
# Exceptions
ValidationError, BusinessLogicError, NotFoundError, 
PermissionError, InventoryError, PaymentError, ConfigurationError

# Cache
get_cache, init_cache, clear_cache, cached, 
invalidate_cache, generate_cache_key

# Decorators
track_performance, performance_log, rate_limit, 
handle_exceptions, role_required

# Helpers
parse_date, get_pagination, json_response, 
allowed_file, get_file_extension, get_week_range, 
get_month_range, safe_template_render

# Filters
format_currency, format_date, format_datetime, 
render_safe, render_safe_data, filter_registry

# CSRF
get_csrf_token, validate_csrf_token, csrf_exempt

# Utility
configure_logging, register_context_processors, 
register_template_filters, register_error_handlers
```

## Configuration

### Cache Configuration

```python
# config.py
CACHE_TYPE = 'redis'  # or 'simple', 'memcached'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 300
```

### Rate Limiting

```python
# config.py
RATELIMIT_STORAGE_URL = 'memory://'
RATELIMIT_DEFAULT = '100/hour'
```

### Email Configuration

```python
# config.py
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@gmail.com'
MAIL_PASSWORD = 'your-app-password'
MAIL_DEFAULT_SENDER = 'your-email@gmail.com'
```

## Best Practices

### 1. Error Handling

Always use custom exceptions for business logic errors:

```python
from app.utils.exceptions import ValidationError, InventoryError

def process_order(order_data):
    try:
        validate_order_data(order_data)
        update_inventory(order_data)
        return create_order(order_data)
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise
    except InventoryError as e:
        logger.error(f"Inventory error: {e}")
        raise
```

### 2. Performance Monitoring

Use performance tracking for critical endpoints:

```python
from app.utils import track_performance

@orders_bp.route('/api/dashboard/data')
@track_performance('dashboard_data_load')
def get_dashboard_data():
    # Dashboard data loading logic
    pass
```

### 3. Caching

Cache expensive operations appropriately:

```python
from app.utils import cached

@cached(timeout=3600)  # 1 hour cache
def get_sales_report(date_range):
    # Expensive report generation
    return report_data
```

### 4. Rate Limiting

Apply rate limiting to API endpoints:

```python
from app.utils import rate_limit

@api_bp.route('/data')
@rate_limit(max_calls=60, period=60)  # 60 calls per minute
def get_api_data():
    return jsonify(data)
```

### 5. Email Templates

Use template-based emails for consistency:

```python
from app.utils.email import send_email

send_email(
    to=user.email,
    subject='Welcome to Our App',
    template='emails/welcome.html',
    user=user,
    confirmation_url=generate_confirmation_url(user)
)
```

## Testing

### Testing Utilities

```python
# test_utils.py
from app.utils import format_currency, parse_date

def test_format_currency():
    assert format_currency(123.45) == '$123.45'
    assert format_currency(None) == 'N/A'

def test_parse_date():
    date = parse_date('2023-12-25')
    assert date.year == 2023
    assert date.month == 12
    assert date.day == 25
```

### Mocking Cache

```python
# test_decorators.py
from app.utils import cached
import unittest.mock

@unittest.mock.patch('app.utils.cache.get_cache')
def test_cached_function(mock_cache):
    mock_cache.return_value.get.return_value = None
    mock_cache.return_value.set.return_value = True
    
    result = expensive_function('test')
    assert result is not None
```

## Troubleshooting

### Common Issues

1. **Cache Not Working**: Check cache configuration and Redis/Memcached connectivity
2. **Rate Limiting Too Strict**: Adjust limits in configuration
3. **Email Not Sending**: Verify SMTP settings and authentication
4. **Performance Tracking Not Showing**: Ensure Sentry is configured
5. **Template Filters Not Working**: Check filter registration in app initialization

### Debug Mode

Enable debug logging for utilities:

```python
import logging
logging.getLogger('app.utils').setLevel(logging.DEBUG)
```

## Contributing

When adding new utilities:

1. Add comprehensive docstrings
2. Include type hints
3. Write unit tests
4. Update this documentation
5. Export from `__init__.py` if commonly used
6. Follow existing code style and patterns

## Dependencies

Some utilities have optional dependencies:

- `flask-limiter` - For rate limiting
- `sentry-sdk` - For performance tracking
- `redis` - For Redis caching
- `memcached` - For Memcached caching

Install with:
```bash
pip install flask-limiter sentry-sdk redis
```

## Security Considerations

- CSRF tokens are validated by default
- Rate limiting prevents abuse
- Input validation in helpers
- Safe template rendering prevents XSS
- Email templates are escaped by default

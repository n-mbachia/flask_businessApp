# Routes Package

This package contains all route blueprints for the Flask business application.

## Structure

```
app/routes/
├── __init__.py          # Blueprint registration and error handlers
├── README.md             # This file - package documentation
├── main.py              # Main dashboard and analytics routes
├── auth.py              # Authentication routes (login, register, etc.)
├── products.py           # Product management routes
├── orders.py             # Order management routes
├── order_item.py         # Order item management routes
├── sales.py              # Sales recording and management
├── customer.py            # Customer management routes
├── costs.py              # Cost tracking routes
├── analytics.py           # Business analytics routes
└── api_docs.py           # API documentation routes
```

## Available Blueprints

| Blueprint | Description | URL Prefix | Main Features |
|-----------|-------------|-------------|---------------|
| `main_bp` | `/` | Dashboard, profit trends, product profitability |
| `auth_bp` | `/auth` | Login, registration, password reset, settings |
| `products_bp` | `/products` | Product CRUD, inventory management, search |
| `orders_bp` | `/orders` | Order management, completion, status updates |
| `order_items_bp` | `/orders` | Add/edit/delete order items, inventory integration |
| `sales_bp` | `/sales` | Sales recording, customer management |
| `customer_bp` | `/customers` | Customer CRUD, search, order history |
| `costs_bp` | `/costs` | Cost tracking, categorization, reporting |
| `analytics_bp` | `/analytics` | Business metrics, trends analysis |
| `storefront_bp` | `/storefront` | Vendor catalog, storefront checkout, customer lookup |
| `api_docs_bp` | `/api/docs` | API documentation and testing interface |

## Security Features

All routes implement comprehensive security measures:

- **Authentication**: `@login_required` decorator on all protected routes
- **Rate Limiting**: `@rate_limit` decorator to prevent abuse
- **Input Validation**: Sanitization and validation of all user inputs
- **Security Logging**: `SecurityUtils.log_security_event()` for audit trails
- **CSRF Protection**: Built-in CSRF token validation
- **Authorization**: User ownership checks for all data access

The storefront blueprint exposes a public catalog and checkout workflow plus a customer lookup endpoint (`/storefront/customer-info`). The checkout flow is CSRF-exempt but still validates ownership, inventory, and customer data before persisting orders tagged with `source=storefront`, so dashboard and inventory metrics stay synchronized.

## API Integration

Most routes support both traditional HTML responses and AJAX/JSON responses:

- **AJAX Detection**: Checks `X-Requested-With` header
- **JSON Responses**: Structured responses with `APIResponse` utility
- **Error Handling**: Consistent error format across all endpoints
- **Status Codes**: Proper HTTP status codes for different scenarios

## Common Patterns

### Form Handling
```python
if form.validate_on_submit():
    try:
        # Process form data
        db.session.commit()
        flash('Success message', 'success')
        return redirect(url_for('endpoint'))
    except Exception as e:
        db.session.rollback()
        flash('Error message', 'error')
        return redirect(url_for('endpoint'))
else:
    # Handle GET request or validation failure
    return render_template('template.html', form=form)
```

### Security Validation
```python
# Input validation
if check_security(input_data, 'all'):
    SecurityUtils.log_security_event('security_issue', {
        'user_id': current_user.id,
        'data': input_data,
        'ip': request.remote_addr
    }, 'warning')
    flash('Invalid input detected', 'danger')
    return redirect(url_for('endpoint'))

# Authorization check
if resource.user_id != current_user.id:
    SecurityUtils.log_security_event('unauthorized_access', {
        'user_id': current_user.id,
        'resource_id': resource.id,
        'ip': request.remote_addr
    }, 'warning')
    abort(403)
```

### Error Handling
```python
try:
    # Database operations
    pass
except Exception as e:
    current_app.logger.error(f"Error description: {str(e)}", exc_info=True)
    db.session.rollback()
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'Error description'
        }), 500
    
    flash('Error description', 'error')
    return redirect(url_for('endpoint'))
```

## Dependencies

All routes depend on:

- **Flask**: Web framework
- **Flask-Login**: User session management
- **SQLAlchemy**: Database ORM
- **Security Utils**: Input validation and security logging
- **Forms**: WTForms for form validation
- **Models**: Database models for data access

## Registration

Blueprints are automatically registered in `app/routes/__init__.py`:

```python
def register_blueprints(app):
    from .main import main_bp
    from .auth import auth_bp
    # ... other imports
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    # ... other registrations
```

## Notes

- All routes use consistent URL patterns and naming conventions
- Security logging is implemented across all modules for audit trails
- Error handling provides both user-friendly messages and detailed logging
- AJAX support is built into all form-handling routes
- Rate limiting prevents abuse and protects performance
- The orders dashboard now surfaces a customer intelligence widget (top buyers, AOV, repeat rate, lifetime revenue) that links directly to the `/customers` endpoint, ensuring storefront and manual shoppers appear in the same business context.
- Storefront checkout creates `Order.source = storefront`, updates/creates customer records (even for guests), and uses `/storefront/customer-info` to prefill saved buyers before persisting the transaction, keeping analytics and inventory synchronized.

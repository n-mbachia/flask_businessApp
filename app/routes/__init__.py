"""
Routes package for the application.

This package contains all of the route blueprints for the application.
"""

def register_blueprints(app):
    """Register all blueprints with the application."""
    # Import blueprints here to avoid circular imports
    from .main import main_bp
    from .auth import auth_bp
    from .products import products_bp
    from .orders import orders_bp
    from .sales import sales_bp
    from .costs import costs_bp
    from .customer import customer_bp
    from .order_item import bp as order_items_bp
    from .api_docs import api_docs_bp
    from .analytics import analytics_bp
    from .storefront import storefront_bp
    
    # Import and register API blueprint
    from app.api.v1 import api_v1_bp, register_namespaces
    
    # Register API blueprint and namespaces (exempt from CSRF)
    from app import csrf
    csrf.exempt(api_v1_bp)
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
        # analytics_api_bp removed; now handled via api_v1_bp
    register_namespaces()
    
    # Register API documentation blueprint
    app.register_blueprint(api_docs_bp, url_prefix='/api/docs')
    
    # Register main blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(order_items_bp, url_prefix='/orders')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(storefront_bp)
    app.register_blueprint(costs_bp, url_prefix='/costs')
    app.register_blueprint(customer_bp, url_prefix='/customers')
    
    # Add URL rules for error handlers
    register_error_handlers(app)

def register_error_handlers(app):
    """Register error handlers for the application."""
    from flask import render_template
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

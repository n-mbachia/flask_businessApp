"""
API v1 package for the application.

This package contains all version 1 API endpoints and functionality.
"""
from flask import Blueprint, jsonify, current_app
from flask_restx import Api, Resource, fields, Namespace

# Create API v1 blueprint
api_v1_bp = Blueprint('api_v1', __name__)

# Initialize Flask-RESTx API
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api = Api(
    api_v1_bp,
    version='1.0',
    title='BusinessApp API',
    description='BusinessApp RESTful API',
    doc='/docs',
    authorizations=authorizations,
    security='apikey',
    default='v1',
    default_label='API v1'
)

def register_namespaces():
    """Register all API namespaces to avoid circular imports."""
    from . import auth, products, sales, inventory, analytics, orders, customers, enhanced_orders, predictive_analytics, dashboard
    
    # Register namespaces
    api.add_namespace(auth.ns, path='/auth')
    api.add_namespace(products.ns, path='/products')
    api.add_namespace(sales.ns, path='/sales')
    api.add_namespace(inventory.ns, path='/inventory')
    api.add_namespace(analytics.ns, path='/analytics')
    api.add_namespace(orders.ns, path='/orders')
    api.add_namespace(customers.ns, path='/customers')
    api.add_namespace(enhanced_orders.ns, path='/enhanced_orders')
    api.add_namespace(predictive_analytics.ns, path='/predictive')
    api.add_namespace(dashboard.ns, path='/dashboard')

# API documentation route
@api.route('/')
class APIV1Root(Resource):
    """API root endpoint providing metadata."""

    def get(self):
        return {
            'name': 'BusinessApp API',
            'version': '1.0',
            'status': 'active',
            'documentation': '/api/v1/docs',
            'endpoints': [
                {'path': '/api/v1/auth', 'methods': ['POST'], 'description': 'Authentication'},
                {'path': '/api/v1/products', 'methods': ['GET', 'POST'], 'description': 'Product management'},
                {'path': '/api/v1/sales', 'methods': ['GET', 'POST'], 'description': 'Sales tracking'},
                {'path': '/api/v1/inventory', 'methods': ['GET', 'PUT'], 'description': 'Inventory management'},
                {'path': '/api/v1/analytics', 'methods': ['GET'], 'description': 'Business analytics'},
                {'path': '/api/v1/orders', 'methods': ['GET', 'POST'], 'description': 'Order management'},
                {'path': '/api/v1/customers', 'methods': ['GET', 'POST'], 'description': 'Customer management'},
                {'path': '/api/v1/enhanced_orders', 'methods': ['GET', 'POST'], 'description': 'Enhanced order operations'}
            ]
        }

# Error handlers
@api.errorhandler
@api_v1_bp.errorhandler
@api_v1_bp.app_errorhandler
@api_v1_bp.app_errorhandler(404)
def default_error_handler(error):
    """Default error handler for the API."""
    if hasattr(error, 'code') and hasattr(error, 'description'):
        return jsonify({
            'success': False,
            'error': error.description,
            'code': error.code
        }), error.code
    
    current_app.logger.error(f"Unhandled error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'An unexpected error occurred',
        'code': 500
    }), 500

__all__ = ['api_v1_bp', 'api', 'register_namespaces']

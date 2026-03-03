"""
Customers API namespace.

This module contains all customer-related API endpoints for enhanced forms.
"""
from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, jsonify
from flask_login import login_required, current_user
from app.models import Customer, db
from app.services.customer_service import CustomerService

# Create namespace
ns = Namespace('customers', description='Customer operations')

# Request parsers
customer_search_parser = reqparse.RequestParser()
customer_search_parser.add_argument('q', type=str, required=False, help='Search query')
customer_search_parser.add_argument('status', type=str, required=False, help='Customer status filter')
customer_search_parser.add_argument('has_orders', type=str, required=False, help='Filter by order history')

# Response models
customer_model = ns.model('Customer', {
    'id': fields.Integer(description='Customer ID'),
    'name': fields.String(description='Customer name'),
    'email': fields.String(description='Customer email'),
    'phone': fields.String(description='Customer phone'),
    'company': fields.String(description='Customer company'),
    'is_active': fields.Boolean(description='Customer active status'),
    'created_at': fields.DateTime(description='Creation date'),
    'order_count': fields.Integer(description='Number of orders'),
    'total_spent': fields.Float(description='Total amount spent')
})

customer_detail_model = ns.model('CustomerDetail', {
    'id': fields.Integer(description='Customer ID'),
    'name': fields.String(description='Customer name'),
    'email': fields.String(description='Customer email'),
    'phone': fields.String(description='Customer phone'),
    'company': fields.String(description='Customer company'),
    'address': fields.String(description='Address line 1'),
    'address2': fields.String(description='Address line 2'),
    'city': fields.String(description='City'),
    'state': fields.String(description='State'),
    'postal_code': fields.String(description='Postal code'),
    'country': fields.String(description='Country'),
    'tax_id': fields.String(description='Tax ID'),
    'notes': fields.String(description='Customer notes'),
    'is_active': fields.Boolean(description='Customer active status'),
    'created_at': fields.DateTime(description='Creation date'),
    'updated_at': fields.DateTime(description='Last update date')
})

@ns.route('/search')
class CustomerSearch(Resource):
    @ns.doc('search_customers')
    @ns.marshal_list_with(customer_model)
    @ns.expect(customer_search_parser)
    @login_required
    def get(self):
        """Search customers with real-time filtering."""
        args = customer_search_parser.parse_args()
        query = args.get('q', '')
        status = args.get('status', '')
        has_orders = args.get('has_orders', '')
        
        try:
            customers = CustomerService.search_customers(
                current_user.id, 
                query, 
                status=status,
                has_orders=has_orders
            )
            
            return [{
                'id': c.id,
                'name': c.name,
                'email': c.email or '',
                'phone': c.phone or '',
                'company': c.company or '',
                'is_active': c.is_active,
                'created_at': c.created_at,
                'order_count': c.get_order_count(),
                'total_spent': float(c.get_total_spent())
            } for c in customers]
            
        except Exception as e:
            ns.abort(500, f'Search failed: {str(e)}')

@ns.route('/<int:customer_id>')
@ns.param('customer_id', 'The customer identifier')
@ns.response(404, 'Customer not found')
class CustomerResource(Resource):
    @ns.doc('get_customer')
    @ns.marshal_with(customer_detail_model)
    @login_required
    def get(self, customer_id):
        """Get customer details for order form."""
        try:
            customer = CustomerService.get_customer(customer_id, current_user.id)
            
            return {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'company': customer.company or '',
                'address': customer.address or '',
                'address2': customer.address2 or '',
                'city': customer.city or '',
                'state': customer.state or '',
                'postal_code': customer.postal_code or '',
                'country': customer.country or '',
                'tax_id': customer.tax_id or '',
                'notes': customer.notes or '',
                'is_active': customer.is_active,
                'created_at': customer.created_at,
                'updated_at': customer.updated_at
            }
            
        except Exception as e:
            if 'not found' in str(e).lower():
                ns.abort(404, 'Customer not found')
            ns.abort(500, f'Failed to get customer: {str(e)}')

@ns.route('/<int:customer_id>/toggle-status')
@ns.param('customer_id', 'The customer identifier')
@ns.response(404, 'Customer not found')
@ns.response(403, 'Forbidden')
class CustomerStatusToggle(Resource):
    @ns.doc('toggle_customer_status')
    @ns.response(200, 'Success', customer_model)
    @login_required
    def post(self, customer_id):
        """Toggle customer active status."""
        try:
            customer = CustomerService.toggle_customer_status(customer_id, current_user.id)
            
            return {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'company': customer.company or '',
                'is_active': customer.is_active,
                'created_at': customer.created_at,
                'order_count': customer.get_order_count(),
                'total_spent': float(customer.get_total_spent())
            }
            
        except Exception as e:
            if 'not found' in str(e).lower():
                ns.abort(404, 'Customer not found')
            ns.abort(500, f'Failed to toggle status: {str(e)}')

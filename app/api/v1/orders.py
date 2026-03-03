"""
Orders API namespace.

This module contains all order-related API endpoints.
"""
from flask_restx import Namespace, Resource, fields, reqparse, abort
from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from app.models import Order, OrderItem, Customer, Product, db
from app.utils.decorators import check_confirmed
from datetime import datetime

# Create namespace
ns = Namespace('orders', description='Order operations')

# Request parsers
order_parser = reqparse.RequestParser()
order_parser.add_argument('customer_id', type=int, required=True, help='Customer ID')
order_parser.add_argument('status', type=str, required=True, help='Order status')
order_parser.add_argument('notes', type=str, required=False, help='Order notes')
order_parser.add_argument('shipping_address', type=dict, required=False, help='Shipping address')
order_parser.add_argument('billing_address', type=dict, required=False, help='Billing address')

# Response models
order_item_model = ns.model('OrderItem', {
    'id': fields.Integer(description='Item ID'),
    'product_id': fields.Integer(description='Product ID'),
    'product_name': fields.String(description='Product name'),
    'quantity': fields.Integer(description='Item quantity'),
    'unit_price': fields.Float(description='Unit price'),
    'total': fields.Float(description='Total price')
})

order_model = ns.model('Order', {
    'id': fields.Integer(description='Order ID'),
    'order_number': fields.String(description='Order number'),
    'customer_id': fields.Integer(description='Customer ID'),
    'customer_name': fields.String(attribute='customer.name', description='Customer name'),
    'status': fields.String(description='Order status'),
    'order_date': fields.DateTime(description='Order date'),
    'total_amount': fields.Float(description='Total amount'),
    'notes': fields.String(description='Order notes'),
    'items': fields.List(fields.Nested(order_item_model), description='Order items')
})

# Error responses
order_not_found = ns.model('Error', {
    'message': fields.String(description='Error message')
})

@ns.route('/')
class OrderList(Resource):
    @ns.doc('list_orders')
    @ns.marshal_list_with(order_model)
    @login_required
    @check_confirmed
    def get(self):
        """List all orders for the current user."""
        return Order.query.filter_by(user_id=current_user.id).all()
    
    @ns.doc('create_order')
    @ns.expect(order_parser)
    @ns.marshal_with(order_model, code=201)
    @ns.response(400, 'Invalid input')
    @ns.response(403, 'Forbidden')
    @login_required
    @check_confirmed
    def post(self):
        """Create a new order."""
        args = order_parser.parse_args()
        
        # Create new order
        order = Order(
            customer_id=args['customer_id'],
            user_id=current_user.id,
            status=args['status'],
            notes=args.get('notes')
        )
        
        db.session.add(order)
        db.session.commit()
        
        return order, 201

@ns.route('/<int:order_id>')
@ns.param('order_id', 'The order identifier')
@ns.response(404, 'Order not found', order_not_found)
@ns.response(403, 'Forbidden', order_not_found)
class OrderResource(Resource):
    @ns.doc('get_order')
    @ns.marshal_with(order_model)
    @login_required
    @check_confirmed
    def get(self, order_id):
        """Fetch an order given its identifier."""
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to access this order')
        return order
    
    @ns.doc('update_order')
    @ns.expect(order_parser)
    @ns.marshal_with(order_model)
    @ns.response(400, 'Invalid input')
    @login_required
    @check_confirmed
    def put(self, order_id):
        """Update an order."""
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to update this order')
            
        args = order_parser.parse_args()
        
        order.customer_id = args['customer_id']
        order.status = args['status']
        order.notes = args.get('notes')
        
        db.session.commit()
        return order
    
    @ns.doc('delete_order')
    @ns.response(204, 'Order deleted')
    @login_required
    @check_confirmed
    def delete(self, order_id):
        """Delete an order."""
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to delete this order')
            
        db.session.delete(order)
        db.session.commit()
        return '', 204


def _parse_iso_date(value: str, label: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        ns.abort(400, f"{label} must be in YYYY-MM-DD format")


@ns.route('/recent')
class RecentOrders(Resource):
    @ns.doc('recent_orders')
    @ns.param('start_date', 'Start of the time window (YYYY-MM-DD)')
    @ns.param('end_date', 'End of the time window (YYYY-MM-DD)')
    @ns.param('limit', 'Maximum number of orders to return')
    @login_required
    @check_confirmed
    def get(self):
        """Return the most recent orders for the authenticated user."""
        args = reqparse.RequestParser()
        args.add_argument('start_date', type=str, location='args')
        args.add_argument('end_date', type=str, location='args')
        args.add_argument('limit', type=int, default=10, location='args')
        params = args.parse_args()

        start_date = _parse_iso_date(params.get('start_date'), 'start_date')
        end_date = _parse_iso_date(params.get('end_date'), 'end_date')
        limit = max(1, min(params.get('limit') or 10, 50))

        query = Order.query.filter(Order.user_id == current_user.id)
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        if end_date:
            query = query.filter(Order.order_date <= end_date)

        orders = query.order_by(Order.order_date.desc()).limit(limit).all()
        payload = []
        for order in orders:
            payload.append({
                'id': order.id,
                'order_number': order.order_number,
                'date': order.order_date.strftime('%Y-%m-%d'),
                'customer': order.customer.name if order.customer else 'Walk-in',
                'amount': float(order.total_amount or 0.0),
                'status': order.status
            })
        return jsonify(payload)


@ns.route('/<int:order_id>/items')
class OrderItems(Resource):
    @ns.doc('add_order_item')
    @ns.expect(order_item_model)
    @ns.marshal_with(order_item_model, code=201)
    @ns.response(400, 'Invalid input')
    @login_required
    @check_confirmed
    def post(self, order_id):
        """Add an item to an order with inventory validation."""
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to modify this order')

        if order.status in ['completed', 'cancelled']:
            ns.abort(400, f'Cannot add items to a {order.status} order')

        data = request.get_json()
        product = Product.query.filter_by(
            id=data['product_id'],
            user_id=current_user.id,
            is_active=True
        ).first()
        if not product:
            ns.abort(404, 'Product not found')

        quantity = data.get('quantity', 1)
        unit_price = data.get('unit_price', product.selling_price_per_unit)

        # Check inventory if needed
        if order.status == 'processing' and product.track_inventory:
            if product.current_stock < quantity:
                ns.abort(400, f'Not enough stock. Only {product.current_stock} available.')

        try:
            with db.session.begin_nested():
                item = OrderItem(
                    order_id=order_id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    notes=data.get('notes', '')
                )
                db.session.add(item)
                order.calculate_total()

                # Update inventory
                if order.status == 'processing' and product.track_inventory:
                    from app.services.inventory_service import InventoryService
                    InventoryService.adjust_inventory(
                        product_id=product.id,
                        quantity=-quantity,
                        adjustment_type='sale',
                        reference_id=order.id,
                        reference_type='order',
                        notes=f'Order #{order.id} item added via API'
                    )
            db.session.commit()
            return item, 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"API add order item error: {str(e)}")
            ns.abort(500, 'Internal server error')

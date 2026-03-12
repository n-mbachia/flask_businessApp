"""Enhanced Order API namespace.

This module contains enhanced order-related API endpoints for dynamic forms.
"""
from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
import flask_login
from werkzeug.exceptions import HTTPException
from decimal import Decimal, InvalidOperation
import logging
from app.models import Product, Order, OrderItem, db
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

# Create namespace
ns = Namespace('enhanced_orders', description='Enhanced order operations')

# Request parsers
product_parser = reqparse.RequestParser()
product_parser.add_argument('product_id', type=int, required=True, help='Product ID')

calc_subtotal_parser = reqparse.RequestParser()
calc_subtotal_parser.add_argument('quantity', type=int, required=True, help='Item quantity')
calc_subtotal_parser.add_argument('unit_price', type=float, required=True, help='Unit price')

calc_totals_parser = reqparse.RequestParser()
calc_totals_parser.add_argument('subtotal', type=float, required=False, default=0.0, help='Order subtotal')
calc_totals_parser.add_argument('tax_rate', type=float, required=False, default=0.0, help='Tax rate percentage')
calc_totals_parser.add_argument('shipping_amount', type=float, required=False, default=0.0, help='Shipping amount')
calc_totals_parser.add_argument('discount_amount', type=float, required=False, default=0.0, help='Discount amount')

status_parser = reqparse.RequestParser()
status_parser.add_argument('status', type=str, required=True, help='Order status')

notes_parser = reqparse.RequestParser()
notes_parser.add_argument('notes', type=str, required=False, help='Order notes')

# Response models
product_model = ns.model('Product', {
    'id': fields.Integer(description='Product ID'),
    'name': fields.String(description='Product name'),
    'description': fields.String(description='Product description'),
    'price': fields.Float(description='Product price'),
    'stock_quantity': fields.Integer(description='Current stock quantity'),
    'track_inventory': fields.Boolean(description='Whether inventory is tracked'),
    'sku': fields.String(description='Product SKU'),
    'image_url': fields.String(description='Product image URL'),
    'is_available': fields.Boolean(description='Product availability')
})

calculation_model = ns.model('Calculation', {
    'subtotal': fields.Float(description='Calculated subtotal'),
    'tax_amount': fields.Float(description='Calculated tax amount'),
    'total': fields.Float(description='Calculated total'),
    'formatted_subtotal': fields.String(description='Formatted subtotal'),
    'formatted_tax_amount': fields.String(description='Formatted tax amount'),
    'formatted_total': fields.String(description='Formatted total')
})

warning_model = ns.model('Warning', {
    'warnings': fields.List(fields.String(), description='Warning messages'),
    'has_warnings': fields.Boolean(description='Whether warnings exist')
})

@ns.route('/product/<int:product_id>')
@ns.param('product_id', 'The product identifier')
@ns.response(404, 'Product not found')
class ProductDetails(Resource):
    @ns.doc('get_product_details')
    @ns.marshal_with(product_model)
    def get(self, product_id):
        """Get product details for order item form."""
        try:
            auth_header = request.headers.get('Authorization')
            is_authenticated = (
                flask_login.current_user
                and getattr(flask_login.current_user, 'is_authenticated', False)
            )
            if not is_authenticated and not auth_header:
                ns.abort(401, 'Authentication required')

            product = Product.query.get_or_404(product_id)
            
            # Check if user has access to this product
            if is_authenticated and hasattr(product, 'user_id') and product.user_id != flask_login.current_user.id:
                ns.abort(403, 'Access denied')
            
            return {
                'id': product.id,
                'name': product.name,
                'description': getattr(product, 'description', ''),
                'price': float(product.price) if hasattr(product, 'price') else float(getattr(product, 'selling_price_per_unit', 0.0)),
                'stock_quantity': product.current_stock if getattr(product, 'track_inventory', False) else None,
                'track_inventory': getattr(product, 'track_inventory', False),
                'sku': getattr(product, 'sku', ''),
                'image_url': getattr(product, 'image_url', ''),
                'is_available': getattr(product, 'is_active', True)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            if 'not found' in str(e).lower():
                ns.abort(404, 'Product not found')
            ns.abort(500, f'Failed to get product details: {str(e)}')

@ns.route('/calculate-item-subtotal')
class CalculateItemSubtotal(Resource):
    @ns.doc('calculate_item_subtotal')
    @ns.marshal_with(calculation_model)
    @ns.expect(calc_subtotal_parser)
    def post(self):
        """Calculate subtotal for order item."""
        try:
            logger.info("Request method: %s", request.method)
            logger.info("Request form data: %s", dict(request.form))

            if request.is_json:
                data = request.get_json(silent=True) or {}
                logger.info("Request JSON data: %s", data)
                quantity_raw = data.get('quantity')
                unit_price_raw = data.get('unit_price')
            else:
                quantity_raw = request.form.get('quantity')
                unit_price_raw = request.form.get('unit_price')

                # If form data is empty, try parsing args
                if quantity_raw is None and unit_price_raw is None:
                    args = calc_subtotal_parser.parse_args()
                    quantity_raw = args.get('quantity')
                    unit_price_raw = args.get('unit_price')

            if quantity_raw is None or unit_price_raw is None:
                logger.error("Calculation error: missing quantity or unit price")
                ns.abort(400, 'error: Quantity and unit price are required')

            # Parse quantity
            try:
                quantity = int(quantity_raw)
            except (ValueError, TypeError):
                logger.error("Calculation error: invalid quantity value")
                ns.abort(400, 'error: Quantity must be a valid integer')

            # Parse unit price
            try:
                unit_price_value = float(unit_price_raw)
            except (ValueError, TypeError):
                logger.error("Calculation error: invalid unit price value")
                ns.abort(400, 'error: Unit price must be a valid number')

            logger.info("Parsed quantity: %s, unit_price: %s", quantity, unit_price_value)
            
            # Validate inputs
            if quantity <= 0:
                logger.error("Calculation error: quantity must be greater than 0")
                ns.abort(400, 'error: Quantity must be greater than 0')
            
            if unit_price_value < 0:
                logger.error("Calculation error: unit price cannot be negative")
                ns.abort(400, 'error: Unit price cannot be negative')

            # Determine precision strategy (favor Decimal for many decimal places)
            unit_price_str = str(unit_price_raw)
            decimal_places = 0
            if '.' in unit_price_str:
                decimal_places = len(unit_price_str.split('.', 1)[1])

            if decimal_places > 2:
                try:
                    unit_price = Decimal(unit_price_str)
                    subtotal = Decimal(quantity) * unit_price
                    subtotal_value = float(subtotal.quantize(Decimal('0.01')))
                except (InvalidOperation, ValueError):
                    ns.abort(400, 'Unit price must be a valid number')
            else:
                subtotal_value = float(quantity * unit_price_value)
            
            result = {
                'subtotal': subtotal_value,
                'tax_amount': 0.0,
                'total': subtotal_value,
                'formatted_subtotal': f"${subtotal_value:.2f}",
                'formatted_tax_amount': "$0.00",
                'formatted_total': f"${subtotal_value:.2f}"
            }
            
            logger.info(f"Calculation result: {result}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Calculation error: %s", str(e), exc_info=True)
            ns.abort(400, f'Calculation failed: {str(e)}')

@ns.route('/calculate-totals')
class CalculateOrderTotals(Resource):
    @ns.doc('calculate_order_totals')
    @ns.marshal_with(calculation_model)
    @ns.expect(calc_totals_parser)
    def post(self):
        """Calculate complete order totals."""
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        def _get_float(key, default=0.0):
            value = data.get(key, default)
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        subtotal = _get_float('subtotal', 0.0)
        tax_rate = _get_float('tax_rate', 0.0)
        shipping = _get_float('shipping_amount', 0.0)
        discount = _get_float('discount_amount', 0.0)

        if subtotal is None or tax_rate is None or shipping is None or discount is None:
            ns.abort(400, 'Invalid numeric input')

        # If unauthenticated, skip tax calculation (for public/form integrations)
        if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
            if not request.headers.get('Authorization'):
                tax_rate = 0.0

        # Validate inputs
        if subtotal < 0:
            ns.abort(400, 'Subtotal cannot be negative')
        
        if tax_rate < 0 or tax_rate > 100:
            ns.abort(400, 'Tax rate must be between 0 and 100')
        
        if shipping < 0:
            ns.abort(400, 'Shipping cannot be negative')
        
        if discount < 0:
            ns.abort(400, 'Discount cannot be negative')
        
        # Calculate totals
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount + shipping - discount
        
        # Ensure total is not negative
        total = max(0, total)
        
        return {
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'total': round(total, 2),
            'formatted_subtotal': f"${subtotal:.2f}",
            'formatted_tax_amount': f"${tax_amount:.2f}",
            'formatted_total': f"${total:.2f}"
        }

@ns.route('/status-change')
class OrderStatusChange(Resource):
    @ns.doc('handle_status_change')
    @ns.marshal_with(warning_model)
    @ns.expect(status_parser)
    def post(self):
        """Handle order status change warnings."""
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        status = (data.get('status') or '').strip()
        if not status:
            ns.abort(400, 'Status is required')
        
        warnings = []
        
        if status == 'completed':
            warnings.append('Order will be marked as completed and inventory will be updated.')
            warnings.append('customer will be notified of order completion.')
        elif status == 'cancelled':
            warnings.append('Order will be cancelled and items will be returned to inventory.')
            warnings.append('customer will be notified of order cancellation.')
        elif status == 'pending':
            warnings.append('Order will be set to pending status.')
        
        return {
            'warnings': warnings,
            'has_warnings': len(warnings) > 0
        }

@ns.route('/validate-notes')
class ValidateOrderNotes(Resource):
    @ns.doc('validate_order_notes')
    @ns.marshal_with(warning_model)
    @ns.expect(notes_parser)
    def post(self):
        """Validate order notes in real-time."""
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        notes = data.get('notes', '') or ''
        
        warnings = []
        
        # Check length
        if len(notes) > 1000:
            warnings.append('Notes cannot exceed 1000 characters.')
        
        # Check for potentially sensitive information
        sensitive_keywords = ['password', 'credit card', 'ssn', 'social security', 'bank account']
        for keyword in sensitive_keywords:
            if keyword.lower() in notes.lower():
                warnings.append(f'Notes contain potentially sensitive information: {keyword}')
        
        # Check for common issues
        if notes and not any(char.isalnum() for char in notes):
            warnings.append('Notes appear to contain only special characters.')
        
        return {
            'warnings': warnings,
            'has_warnings': len(warnings) > 0
        }

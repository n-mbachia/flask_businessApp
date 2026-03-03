"""
Products API endpoints.

This module contains RESTful API endpoints for product management,
aligned with the product model and improvements from the routes.
"""
from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
import logging

from app.middleware.rate_limiter import api_rate_limit
from app import db
from app.models import Product, InventoryMovement, InventoryLog, Sales
from app.utils.decorators import handle_exceptions
from app.security import SecurityUtils
from app.validators import sanitize_input, check_security, validate_entity
from app.services.dashboard_metrics import DashboardMetrics
from app.services.lot_analytics import LotAnalytics, AnalyticsError
from app.services.predictive_analytics import PredictiveAnalytics

logger = logging.getLogger(__name__)

# Create namespace
ns = Namespace('products', description='Product operations')


# Helper function to generate SKU (same as in routes)
def _generate_sku(product_name: str, user_id: int) -> str:
    import re
    import uuid
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', product_name.upper())
    name_prefix = clean_name[:6] if clean_name else 'PROD'
    user_prefix = f"U{user_id % 1000:03d}"
    random_suffix = str(uuid.uuid4())[:8].upper()
    sku = f"{name_prefix}-{user_prefix}-{random_suffix}"
    counter = 1
    original_sku = sku
    while Product.query.filter_by(sku=sku).first():
        sku = f"{original_sku}-{counter}"
        counter += 1
        if counter > 100:
            sku = f"PROD-{user_prefix}-{uuid.uuid4().hex[:8].upper()}"
            break
    return sku


# Response models for Swagger
product_model = ns.model('Product', {
    'id': fields.Integer(description='Product ID'),
    'name': fields.String(description='Product name'),
    'description': fields.String(description='Product description'),
    'image_url': fields.String(description='Product image URL'),
    'image_filename': fields.String(description='Uploaded filename'),
    'sku': fields.String(description='Stock Keeping Unit'),
    'barcode': fields.String(description='Barcode'),
    'category': fields.String(description='Product category'),
    'cogs_per_unit': fields.Float(description='Cost of goods sold per unit'),
    'selling_price_per_unit': fields.Float(description='Selling price per unit'),
    'margin_threshold': fields.Float(description='Custom margin threshold'),
    'reorder_level': fields.Integer(description='Reorder level'),
    'current_stock': fields.Integer(description='Current stock level (computed)'),
    'total_value': fields.Float(description='Total inventory value (computed)'),
    'margin_percentage': fields.Float(description='Profit margin percentage'),
    'effective_margin_threshold': fields.Float(description='Effective margin threshold (user or custom)'),
    'is_below_reorder_level': fields.Boolean(description='Stock below reorder level'),
    'is_below_margin_threshold': fields.Boolean(description='Margin below threshold'),
    'is_active': fields.Boolean(description='Product active status'),
    'track_inventory': fields.Boolean(description='Whether inventory tracking is enabled'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'updated_at': fields.DateTime(description='Last update timestamp')
})

product_create_model = ns.model('ProductCreate', {
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Product description'),
    'sku': fields.String(description='SKU (optional, auto-generated if empty)'),
    'barcode': fields.String(description='Barcode'),
    'category': fields.String(description='Product category', default='Uncategorized'),
    'cogs_per_unit': fields.Float(required=True, description='COGS per unit'),
    'selling_price_per_unit': fields.Float(required=True, description='Selling price per unit'),
    'reorder_level': fields.Integer(description='Reorder level', default=10),
    'initial_quantity': fields.Integer(description='Initial stock quantity', default=0),
    'track_inventory': fields.Boolean(description='Enable inventory tracking', default=True),
    'margin_threshold': fields.Float(description='Custom margin threshold'),
    'is_active': fields.Boolean(description='Active status', default=True)
})

product_update_model = ns.model('ProductUpdate', {
    'name': fields.String(description='Product name'),
    'description': fields.String(description='Product description'),
    'sku': fields.String(description='SKU'),
    'barcode': fields.String(description='Barcode'),
    'category': fields.String(description='Product category'),
    'cogs_per_unit': fields.Float(description='COGS per unit'),
    'selling_price_per_unit': fields.Float(description='Selling price per unit'),
    'reorder_level': fields.Integer(description='Reorder level'),
    'track_inventory': fields.Boolean(description='Enable inventory tracking'),
    'margin_threshold': fields.Float(description='Custom margin threshold'),
    'is_active': fields.Boolean(description='Active status')
})

error_model = ns.model('Error', {
    'message': fields.String(description='Error message'),
    'details': fields.String(description='Error details')
})


@ns.route('/')
class ProductList(Resource):
    @ns.doc('list_products')
    @ns.marshal_list_with(product_model)
    @ns.response(429, 'Rate limit exceeded')
    @login_required
    @api_rate_limit
    @handle_exceptions
    def get(self):
        """Get all products for the current user."""
        products = Product.query.filter_by(user_id=current_user.id).all()
        return products

    @ns.doc('create_product')
    @ns.expect(product_create_model)
    @ns.marshal_with(product_model, code=201)
    @ns.response(400, 'Validation error', error_model)
    @ns.response(429, 'Rate limit exceeded')
    @login_required
    @api_rate_limit
    @handle_exceptions
    def post(self):
        """Create a new product for the current user."""
        data = request.get_json()

        if not data.get('name'):
            ns.abort(400, message='Product name is required')

        name = sanitize_input(data['name'], 'html')
        description = sanitize_input(data.get('description', ''), 'html')
        sku = sanitize_input(data.get('sku', ''), 'html')
        barcode = sanitize_input(data.get('barcode', ''), 'html')
        category = sanitize_input(data.get('category', 'Uncategorized'), 'html')

        if check_security(name, 'all') or check_security(description, 'all'):
            SecurityUtils.log_security_event('api_product_security_issue', {
                'user_id': current_user.id,
                'data': data,
                'ip': request.remote_addr
            }, 'warning')
            ns.abort(400, message='Invalid input detected')

        existing = Product.query.filter_by(name=name, user_id=current_user.id).first()
        if existing:
            ns.abort(400, message='Product name already exists')

        product = Product(
            user_id=current_user.id,
            name=name,
            description=description,
            category=category,
            cogs_per_unit=data['cogs_per_unit'],
            selling_price_per_unit=data['selling_price_per_unit'],
            reorder_level=data.get('reorder_level', 10),
            track_inventory=data.get('track_inventory', True),
            margin_threshold=data.get('margin_threshold'),
            is_active=data.get('is_active', True)
        )

        if not sku:
            product.sku = _generate_sku(name, current_user.id)
        else:
            if Product.query.filter_by(sku=sku, user_id=current_user.id).first():
                ns.abort(400, message='SKU already exists')
            product.sku = sku

        if barcode:
            if Product.query.filter_by(barcode=barcode, user_id=current_user.id).first():
                ns.abort(400, message='Barcode already exists')
            product.barcode = barcode

        db.session.add(product)
        db.session.commit()

        initial_qty = data.get('initial_quantity', 0)
        if initial_qty > 0:
            movement = InventoryMovement(
                product_id=product.id,
                movement_type='receipt',
                quantity=initial_qty,
                unit_cost=product.cogs_per_unit,
                notes='Initial stock via API creation'
            )
            db.session.add(movement)
            db.session.commit()

        SecurityUtils.log_security_event('api_product_created', {
            'user_id': current_user.id,
            'product_id': product.id,
            'product_name': product.name,
            'ip': request.remote_addr
        }, 'info')

        return product, 201


@ns.route('/<int:product_id>')
@ns.param('product_id', 'The product identifier')
@ns.response(404, 'Product not found', error_model)
@ns.response(403, 'Forbidden', error_model)
class ProductResource(Resource):
    @ns.doc('get_product')
    @ns.marshal_with(product_model)
    @login_required
    @handle_exceptions
    def get(self, product_id):
        """Get a specific product for the current user."""
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, message='Product not found')
        return product

    @ns.doc('update_product')
    @ns.expect(product_update_model)
    @ns.marshal_with(product_model)
    @ns.response(400, 'Validation error', error_model)
    @login_required
    @handle_exceptions
    def put(self, product_id):
        """Update a product (partial updates allowed)."""
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, message='Product not found')

        data = request.get_json()
        updatable_fields = [
            'name', 'description', 'sku', 'barcode', 'category',
            'cogs_per_unit', 'selling_price_per_unit', 'reorder_level',
            'track_inventory', 'margin_threshold', 'is_active'
        ]

        for field in updatable_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = sanitize_input(value, 'html')
                    if check_security(value, 'all'):
                        SecurityUtils.log_security_event('api_product_update_security_issue', {
                            'user_id': current_user.id,
                            'product_id': product_id,
                            'field': field,
                            'ip': request.remote_addr
                        }, 'warning')
                        ns.abort(400, message='Invalid input detected')
                setattr(product, field, value)

        if 'name' in data and data['name'] != product.name:
            existing = Product.query.filter(
                Product.name == data['name'],
                Product.user_id == current_user.id,
                Product.id != product_id
            ).first()
            if existing:
                ns.abort(400, message='Product name already exists')

        if 'sku' in data and data['sku'] and data['sku'] != product.sku:
            existing = Product.query.filter(
                Product.sku == data['sku'],
                Product.user_id == current_user.id,
                Product.id != product_id
            ).first()
            if existing:
                ns.abort(400, message='SKU already exists')

        if 'barcode' in data and data['barcode'] and data['barcode'] != product.barcode:
            existing = Product.query.filter(
                Product.barcode == data['barcode'],
                Product.user_id == current_user.id,
                Product.id != product_id
            ).first()
            if existing:
                ns.abort(400, message='Barcode already exists')

        db.session.commit()
        SecurityUtils.log_security_event('api_product_updated', {
            'user_id': current_user.id,
            'product_id': product.id,
            'product_name': product.name,
            'ip': request.remote_addr
        }, 'info')
        return product

    @ns.doc('delete_product')
    @ns.response(204, 'Product deleted')
    @ns.response(404, 'Product not found', error_model)
    @login_required
    @handle_exceptions
    def delete(self, product_id):
        """Delete a product for the current user."""
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, message='Product not found')

        SecurityUtils.log_security_event('api_product_deleted', {
            'user_id': current_user.id,
            'product_id': product.id,
            'product_name': product.name,
            'ip': request.remote_addr
        }, 'info')

        db.session.delete(product)
        db.session.commit()
        return '', 204


@ns.route('/search')
class ProductSearch(Resource):
    @ns.doc('search_products')
    @ns.param('q', 'Search query')
    @ns.param('page', 'Page number', type=int, default=1)
    @ns.param('per_page', 'Items per page', type=int, default=10)
    @ns.marshal_list_with(product_model)
    @ns.response(400, 'Invalid query', error_model)
    @login_required
    @api_rate_limit
    @handle_exceptions
    def get(self):
        """Search products by name or SKU."""
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)

        if not query:
            return []

        if len(query) > 100:
            ns.abort(400, message='Search query too long')

        sanitized_query = sanitize_input(query, 'search')
        if check_security(sanitized_query, 'all'):
            SecurityUtils.log_security_event('api_product_search_security_issue', {
                'user_id': current_user.id,
                'query': query,
                'ip': request.remote_addr
            }, 'warning')
            ns.abort(400, message='Invalid search query')

        search = f"%{sanitized_query}%"
        products = Product.query.filter(
            Product.user_id == current_user.id,
            Product.is_active == True,
            (Product.name.ilike(search)) | (Product.sku.ilike(search))
        ).paginate(page=page, per_page=per_page, error_out=False)

        SecurityUtils.log_security_event('api_product_search', {
            'user_id': current_user.id,
            'query': query,
            'results_count': products.total,
            'ip': request.remote_addr
        }, 'info')

        return products.items


# ----------------------------
# Product Analytics Endpoints
# ----------------------------

analytics_parser = reqparse.RequestParser()
analytics_parser.add_argument('period', type=int, default=30, help='Number of days for data aggregation')
analytics_parser.add_argument('start_date', type=str, help='Start date (YYYY-MM-DD)')
analytics_parser.add_argument('end_date', type=str, help='End date (YYYY-MM-DD)')
analytics_parser.add_argument('page', type=int, default=1, help='Page number')
analytics_parser.add_argument('page_size', type=int, default=10, help='Items per page')


@ns.route('/<int:product_id>/analytics/metrics')
class ProductMetrics(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Get key metrics for a product."""
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        dashboard = DashboardMetrics(current_user.id)

        revenue = dashboard.calculate_revenue(product)
        net_profit = dashboard.calculate_net_profit(product)
        margin = dashboard.calculate_net_margin(product)
        units_sold = dashboard.calculate_units_sold(product)

        return {
            'revenue': revenue,
            'net_profit': net_profit,
            'net_margin': margin,
            'units_sold': units_sold,
            'current_stock': product.current_stock,
            'reorder_level': product.reorder_level
        }


@ns.route('/<int:product_id>/analytics/revenue-trend')
class ProductRevenueTrend(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Get revenue trend for a product over time."""
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        dashboard = DashboardMetrics(current_user.id)
        trends = dashboard.get_revenue_profit_trends(product_id, months=args['period'] // 30)
        return {
            'labels': trends.get('dates', []),
            'revenue': trends.get('revenue', [])
        }


@ns.route('/<int:product_id>/analytics/cost-breakdown')
class ProductCostBreakdown(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Get cost breakdown for a product."""
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        dashboard = DashboardMetrics(current_user.id)
        cost_data = dashboard.get_cost_breakdown(product_id)

        labels = cost_data.get('categories', [])
        values = cost_data.get('amounts', [])
        total = round(sum(values), 2)

        return {
            'labels': labels,
            'values': values,
            'total': total
        }


@ns.route('/<int:product_id>/analytics/lot-analytics')
class ProductLotAnalytics(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        try:
            lots_data = LotAnalytics.get_lots_performance_summary(
                user_id=current_user.id,
                product_id=product_id
            )
            all_lots = lots_data.get('lots', [])
        except AnalyticsError as e:
            logger.warning(f"Lot analytics unavailable: {str(e)}")
            all_lots = []
        except Exception as e:
            logger.error(f"Unexpected error in lot analytics: {str(e)}")
            all_lots = []

        page = args['page']
        page_size = args['page_size']
        total = len(all_lots)
        start = (page - 1) * page_size
        paginated = all_lots[start:start + page_size]
        total_pages = (total + page_size - 1) // page_size

        cleaned_lots = []
        for lot in paginated:
            quantity_received = lot.get('initial_quantity', 0)
            units_sold = lot.get('units_sold', 0)
            remaining_quantity = lot.get('remaining_quantity', 0)
            cleaned_lots.append({
                'id': lot.get('lot_id'),
                'lot_number': lot.get('lot_number'),
                'product_id': lot.get('product_id'),
                'product_name': lot.get('product_name'),
                'quantity_received': quantity_received,
                'quantity_sold': units_sold,
                'quantity_remaining': remaining_quantity,
                'sell_through_rate': lot.get('sell_through_rate', 0.0),
                'gross_margin': lot.get('gross_margin', 0.0),
                'status': lot.get('status', 'active'),
                'expiration_status': lot.get('expiration_status', 'good'),
                'created_at': lot.get('created_at') or lot.get('received_date'),
                'days_since_received': lot.get('days_since_received')
            })

        pagination = {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'start': start + 1 if total else 0,
            'end': min(start + page_size, total)
        }

        product_list = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
        products_payload = [{'id': p.id, 'name': p.name} for p in product_list]

        return {
            'data': cleaned_lots,
            'pagination': pagination,
            'products': products_payload
        }

@ns.route('/<int:product_id>/analytics/lot-performance')
class ProductLotPerformance(Resource):
    @login_required
    def get(self, product_id):
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        try:
            lots_data = LotAnalytics.get_lots_performance_summary(
                user_id=current_user.id,
                product_id=product_id
            )
            lots = lots_data.get('lots', [])
        except AnalyticsError as e:
            logger.warning(f"Lot performance unavailable: {str(e)}")
            lots = []
        except Exception as e:
            logger.error(f"Unexpected error in lot performance: {str(e)}")
            lots = []

        lot_labels = []
        sell_through_rates = []
        gross_margins = []

        for lot in lots:
            lot_labels.append(lot.get('lot_number') or f"Lot-{lot.get('lot_id')}")
            sell_through_rates.append(round(lot.get('sell_through_rate', 0.0), 2))
            gross_margins.append(round(lot.get('gross_margin', 0.0), 2))

        dashboard = DashboardMetrics(current_user.id)
        growth_metrics = dashboard.get_growth_metrics(product_id)

        growth_labels = [entry.get('period') for entry in growth_metrics]
        revenue_growth = [entry.get('revenue_growth', 0.0) for entry in growth_metrics]
        velocity_growth = [entry.get('velocity_growth', 0.0) for entry in growth_metrics]

        return {
            'labels': lot_labels,
            'sell_through_rates': sell_through_rates,
            'gross_margins': gross_margins,
            'growth_labels': growth_labels,
            'revenue_growth': revenue_growth,
            'velocity_growth': velocity_growth
        }


@ns.route('/<int:product_id>/analytics/inventory-levels')
class ProductInventoryLevels(Resource):
    @login_required
    def get(self, product_id):
        """Get historical inventory levels from logs."""
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        logs = InventoryLog.query.filter_by(product_id=product_id).order_by(InventoryLog.created_at).all()
        labels = [log.created_at.strftime('%Y-%m-%d') for log in logs]
        current_stock_series = [log.quantity_after for log in logs]

        if not labels:
            labels = [datetime.utcnow().strftime('%Y-%m-%d')]
            current_stock_series = [product.current_stock]

        reorder_level_series = [product.reorder_level] * len(labels)

        current_stock_value = max(product.current_stock, 0)
        reorder_threshold = max(product.reorder_level or 0, 0)
        in_stock_value = max(current_stock_value - reorder_threshold, 0)
        needs_reorder = max(reorder_threshold - current_stock_value, 0)
        out_of_stock_value = 1 if current_stock_value <= 0 else 0

        stock_status_values = [in_stock_value, needs_reorder, out_of_stock_value]
        if all(val == 0 for val in stock_status_values):
            stock_status_values[0] = current_stock_value or 1

        return {
            'labels': labels,
            'current_stock': current_stock_series,
            'reorder_level': reorder_level_series,
            'stock_status_labels': ['In Stock', 'Needs Reorder', 'Out of Stock'],
            'stock_status_values': stock_status_values
        }


@ns.route('/<int:product_id>/analytics/profit-margins')
class ProductProfitMargins(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Get profit margin trend over time."""
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        dashboard = DashboardMetrics(current_user.id)
        trends = dashboard.get_revenue_profit_trends(product_id, months=args['period'] // 30)
        gross_margins = []
        net_margins = []
        for i, rev in enumerate(trends.get('revenue', [])):
            profit_val = trends.get('profit', [])[i] if i < len(trends.get('profit', [])) else 0
            margin = (profit_val / rev * 100) if rev else 0
            gross_margins.append(round(margin, 2))
            net_margins.append(round(margin, 2))
        return {
            'labels': trends.get('dates', []),
            'gross_margins': gross_margins,
            'net_margins': net_margins
        }


@ns.route('/<int:product_id>/analytics/sales-performance')
class ProductSalesPerformance(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Get sales performance data (units sold, revenue) over time."""
        args = analytics_parser.parse_args()
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        dashboard = DashboardMetrics(current_user.id)
        trends = dashboard.get_revenue_profit_trends(product_id, months=args['period'] // 30)
        return {
            'labels': trends.get('dates', []),
            'revenue': trends.get('revenue', []),
            'profit': trends.get('profit', []),
            'units_sold': trends.get('units', [])
        }


@ns.route('/<int:product_id>/analytics/forecasts')
class ProductForecasts(Resource):
    @login_required
    def get(self, product_id):
        """Placeholder for demand forecasts."""
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')
        try:
            historical_query = db.session.query(
                Sales.month,
                func.sum(Sales.total_revenue).label('total_revenue')
            ).filter(
                Sales.product_id == product_id,
                Sales.user_id == current_user.id
            ).group_by(Sales.month).order_by(Sales.month.desc()).limit(6).all()

            history = list(reversed(historical_query))
            historical_revenue = [float(row.total_revenue or 0) for row in history]

            last_label = history[-1].month if history else datetime.utcnow().strftime('%Y-%m')
            base_date = datetime.strptime(f"{last_label}-01", '%Y-%m-%d')

            forecast_result = PredictiveAnalytics.forecast_revenue(current_user.id, periods=6)
            predictions = forecast_result.predictions or []
            if not predictions:
                predictions = [0.0] * 3

            forecast_periods = len(predictions)
            forecast_labels = [
                (base_date + relativedelta(months=i)).strftime('%Y-%m')
                for i in range(1, forecast_periods + 1)
            ]

            unit_price = float(product.selling_price_per_unit or 1.0)
            predicted_demand = [
                int(pred // unit_price) if unit_price else 0
                for pred in predictions
            ]

            return {
                'forecast_labels': forecast_labels,
                'historical_revenue': historical_revenue,
                'forecast_revenue': [float(pred) for pred in predictions],
                'demand_labels': forecast_labels,
                'predicted_demand': predicted_demand,
                'trend_direction': forecast_result.trend_direction,
                'accuracy_score': forecast_result.accuracy_score
            }
        except Exception as e:
            logger.error(f"Error building forecast data for product {product_id}: {str(e)}", exc_info=True)
            return {
                'forecast_labels': [],
                'historical_revenue': [],
                'forecast_revenue': [],
                'demand_labels': [],
                'predicted_demand': []
            }


# ----- Additional endpoint without /analytics (to match frontend) -----
@ns.route('/<int:product_id>/lot-analytics')
class ProductLotAnalyticsLegacy(Resource):
    @login_required
    @ns.expect(analytics_parser)
    def get(self, product_id):
        """Legacy endpoint for lot analytics (without /analytics)."""
        # Reuse the analytics endpoint
        return ProductLotAnalytics().get(product_id)

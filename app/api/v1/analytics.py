# app/api/v1/analytics.py

"""
Analytics API endpoints.
This module contains all analytics-related API endpoints with proper validation.
"""

from flask_login import login_required, current_user
from flask import request
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import func
from flask_restx import Namespace, Resource, fields, reqparse, abort

# Import validation schemas
from app.validators.analytics_validators import (
    SalesByMonthQuery, ProductSalesQuery, CustomerSalesQuery,
    RevenueAnalyticsQuery, FunnelAnalyticsQuery, TopProductsQuery
)

# Import services
from app.services.analytics_service import AnalyticsService
from app import db
from app.models import Order, OrderItem, Product

# Import rate limiting
from app.middleware.rate_limiter import api_rate_limit

# Create namespace
ns = Namespace('analytics', description='Analytics operations')

# Response models
sales_summary_model = ns.model('SalesSummary', {
    'total_sales': fields.Float(description='Total sales amount'),
    'total_orders': fields.Integer(description='Total number of orders'),
    'average_order_value': fields.Float(description='Average order value'),
    'top_products': fields.List(fields.Raw, description='Top selling products')
})

inventory_summary_model = ns.model('InventorySummary', {
    'total_items': fields.Integer(description='Total inventory items'),
    'low_stock_items': fields.Integer(description='Number of items below reorder level'),
    'inventory_value': fields.Float(description='Total inventory value'),
    'categories': fields.List(fields.Raw, description='Inventory by category')
})

error_model = ns.model('Error', {
    'error': fields.String(description='Error message'),
    'details': fields.String(description='Error details'),
    'validation_errors': fields.List(fields.Raw(), description='Validation errors')
})

@ns.route('/sales/monthly')
class MonthlySalesAnalytics(Resource):
    @ns.marshal_with(sales_summary_model)
    @ns.doc('get_monthly_sales')
    @ns.response(429, 'Rate limit exceeded')
    @login_required
    @api_rate_limit
    def get(self):
        """Get monthly sales analytics with validation."""
        try:
            # Parse and validate query parameters
            query_params = {
                'user_id': current_user.id,
                'year': request.args.get('year', type=int),
                'month': request.args.get('month', type=int),
                'limit': request.args.get('limit', 12, type=int)
            }
            
            # Validate using Pydantic
            validated_query = SalesByMonthQuery(**query_params)
            
            # Get data using validated parameters
            sales_data = AnalyticsService.get_sales_by_month(
                user_id=validated_query.user_id,
                year=validated_query.year,
                month=validated_query.month,
                limit=validated_query.limit
            )
            
            return {
                'success': True,
                'data': sales_data,
                'count': len(sales_data)
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': 'Validation error',
                'details': str(e)
            }, 400
        except Exception as e:
            return {
                'success': False,
                'error': 'Internal server error',
                'details': 'Failed to retrieve monthly sales data'
            }, 500

@ns.route('/inventory')
class InventoryAnalytics(Resource):
    @ns.marshal_with(inventory_summary_model)
    @ns.response(429, 'Rate limit exceeded')
    @login_required
    @api_rate_limit
    def get(self):
        """Get inventory analytics summary."""
        try:
            inventory_data = AnalyticsService.get_inventory_summary(current_user.id)
            return inventory_data
        except ValueError as e:
            return {
                'success': False,
                'error': 'Validation error',
                'details': str(e)
            }, 400
        except Exception as e:
            return {
                'success': False,
                'error': 'Internal server error',
                'details': 'Failed to retrieve inventory data'
            }, 500


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None


def _get_date_window():
    end_date = _parse_date(request.args.get('end_date'))
    start_date = _parse_date(request.args.get('start_date'))

    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    return start_date, end_date


def _get_bucket_expression(group_by: str):
    """Return a SQL expression for grouping orders based on the database dialect."""
    bucket = (group_by or 'day').lower()
    bind = db.session.get_bind() or db.engine
    dialect_name = getattr(getattr(bind, 'dialect', None), 'name', '') or ''
    dialect_name = dialect_name.lower()
    is_postgres = 'postgresql' in dialect_name

    if bucket == 'month':
        if is_postgres:
            return func.to_char(func.date_trunc('month', Order.order_date), 'YYYY-MM')
        return func.strftime('%Y-%m', Order.order_date)

    if bucket == 'week':
        if is_postgres:
            return func.to_char(func.date_trunc('week', Order.order_date), 'IYYY-"W"IW')
        return func.strftime('%Y-W%W', Order.order_date)

    # Default to day grouping
    if is_postgres:
        return func.to_char(func.date_trunc('day', Order.order_date), 'YYYY-MM-DD')
    return func.strftime('%Y-%m-%d', Order.order_date)


@ns.route('/kpi')
class AnalyticsKPI(Resource):
    @login_required
    @api_rate_limit
    def get(self):
        """KPI payload for analytics dashboard."""
        try:
            start_date, end_date = _get_date_window()
            period_days = max(1, (end_date - start_date).days)
            prev_start = start_date - timedelta(days=period_days)
            prev_end = start_date

            current = db.session.query(
                func.coalesce(func.sum(Order.total_amount), 0.0).label('revenue'),
                func.count(Order.id).label('orders')
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).first()

            previous = db.session.query(
                func.coalesce(func.sum(Order.total_amount), 0.0).label('revenue'),
                func.count(Order.id).label('orders')
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= prev_start,
                Order.order_date < prev_end
            ).first()

            current_revenue = float(current.revenue or 0.0)
            current_orders = int(current.orders or 0)
            current_aov = (current_revenue / current_orders) if current_orders > 0 else 0.0

            prev_revenue = float(previous.revenue or 0.0)
            prev_orders = int(previous.orders or 0)
            prev_aov = (prev_revenue / prev_orders) if prev_orders > 0 else 0.0

            def growth(cur, prev):
                if prev == 0:
                    return 100.0 if cur > 0 else 0.0
                return ((cur - prev) / prev) * 100.0

            top_cat = db.session.query(
                Product.category.label('category'),
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).label('revenue')
            ).join(
                Product, Product.id == OrderItem.product_id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(
                Product.category
            ).order_by(
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).desc()
            ).first()

            top_category = {
                'name': (top_cat.category if top_cat else '-') or 'Uncategorized',
                'revenue': float(top_cat.revenue or 0.0) if top_cat else 0.0
            }

            # Funnel placeholders (can be replaced by event analytics later)
            purchases = current_orders
            checkouts = purchases
            cart_adds = purchases
            visitors = purchases

            return {
                'total_revenue': current_revenue,
                'total_orders': current_orders,
                'avg_order_value': current_aov,
                'top_category': top_category,
                'revenue_growth': growth(current_revenue, prev_revenue),
                'orders_growth': growth(current_orders, prev_orders),
                'aov_growth': growth(current_aov, prev_aov),
                'visitors': visitors,
                'cart_adds': cart_adds,
                'checkouts': checkouts,
                'purchases': purchases,
                'visitor_to_cart_rate': 100.0 if visitors else 0.0,
                'cart_to_checkout_rate': 100.0 if cart_adds else 0.0,
                'checkout_to_purchase_rate': 100.0 if checkouts else 0.0
            }
        except Exception as e:
            return {
                'error': 'Failed to load KPI analytics',
                'details': str(e)
            }, 500


@ns.route('/revenue')
class AnalyticsRevenue(Resource):
    @login_required
    @api_rate_limit
    def get(self):
        """Revenue time-series for analytics dashboard."""
        try:
            start_date, end_date = _get_date_window()
            group_by = (request.args.get('group_by') or 'day').lower()

            bucket = _get_bucket_expression(group_by)

            rows = db.session.query(
                bucket.label('bucket'),
                func.coalesce(func.sum(Order.total_amount), 0.0).label('revenue')
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(
                bucket
            ).order_by(
                bucket.asc()
            ).all()

            return [{'date': row.bucket, 'revenue': float(row.revenue or 0.0)} for row in rows]
        except Exception as e:
            return {
                'error': 'Failed to load revenue analytics',
                'details': str(e)
            }, 500


@ns.route('/categories')
class AnalyticsCategories(Resource):
    @login_required
    @api_rate_limit
    def get(self):
        """Category revenue breakdown for analytics dashboard."""
        try:
            start_date, end_date = _get_date_window()

            rows = db.session.query(
                Product.category.label('category'),
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).label('revenue')
            ).join(
                Product, Product.id == OrderItem.product_id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(
                Product.category
            ).order_by(
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).desc()
            ).all()

            return [{
                'category': (row.category or 'Uncategorized'),
                'revenue': float(row.revenue or 0.0)
            } for row in rows]
        except Exception as e:
            return {
                'error': 'Failed to load category analytics',
                'details': str(e)
            }, 500


@ns.route('/products/top')
class AnalyticsTopProducts(Resource):
    @login_required
    @api_rate_limit
    def get(self):
        """Top products by revenue for analytics dashboard."""
        try:
            start_date, end_date = _get_date_window()
            limit = request.args.get('limit', 10, type=int) or 10
            limit = max(1, min(limit, 50))

            rows = db.session.query(
                Product.id.label('product_id'),
                Product.name.label('name'),
                Product.category.label('category'),
                func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold'),
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).label('total_revenue')
            ).join(
                Product, Product.id == OrderItem.product_id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == current_user.id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(
                Product.id, Product.name, Product.category
            ).order_by(
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).desc()
            ).limit(limit).all()

            return [{
                'product_id': row.product_id,
                'name': row.name,
                'category': row.category or 'Uncategorized',
                'units_sold': int(row.units_sold or 0),
                'total_revenue': float(row.total_revenue or 0.0)
            } for row in rows]
        except Exception as e:
            return {
                'error': 'Failed to load top products analytics',
                'details': str(e)
            }, 500

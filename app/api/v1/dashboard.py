"""
Dashboard API endpoints used by the interactive main dashboard.
"""
from datetime import datetime, timedelta

from flask import request
from flask_login import current_user, login_required
from flask_restx import Namespace, Resource
from sqlalchemy import func

from app import db
from app.models import Order, OrderItem, Product, Customer
from app.services.profit_calculator import ProfitCalculator
from app.services.business_metrics import BusinessMetrics

ns = Namespace('dashboard', description='Dashboard operations')

PERIOD_DAYS = {
    '7d': 7,
    '30d': 30,
    '90d': 90,
    '1m': 30,
    '3m': 90,
    '6m': 180,
    '1y': 365,
}


def _resolve_period():
    period = request.args.get('period', '6m')
    return period, PERIOD_DAYS.get(period, 180)


def _date_window():
    _, days = _resolve_period()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def _growth(current, previous):
    if previous in (0, None):
        return 0.0
    return round(((current - previous) / previous) * 100.0, 2)


@ns.route('/initial')
class DashboardInitial(Resource):
    method_decorators = [login_required]

    def get(self):
        start_date, end_date = _date_window()
        period, days = _resolve_period()

        revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0.0)).filter(
            Order.user_id == current_user.id,
            Order.status == Order.STATUS_COMPLETED,
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).scalar() or 0.0

        orders_count = db.session.query(func.count(Order.id)).filter(
            Order.user_id == current_user.id,
            Order.status == Order.STATUS_COMPLETED,
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).scalar() or 0

        customer_count = db.session.query(func.count(func.distinct(Order.customer_id))).filter(
            Order.user_id == current_user.id,
            Order.status == Order.STATUS_COMPLETED,
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).scalar() or 0

        prev_end = start_date
        prev_start = prev_end - timedelta(days=days)
        prev_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0.0)).filter(
            Order.user_id == current_user.id,
            Order.status == Order.STATUS_COMPLETED,
            Order.order_date >= prev_start,
            Order.order_date < prev_end
        ).scalar() or 0.0

        prev_orders = db.session.query(func.count(Order.id)).filter(
            Order.user_id == current_user.id,
            Order.status == Order.STATUS_COMPLETED,
            Order.order_date >= prev_start,
            Order.order_date < prev_end
        ).scalar() or 0

        profit_calc = ProfitCalculator(current_user.id)
        profit_summary = profit_calc.get_profit_summary(start_date=start_date, end_date=end_date)
        trend_months = max(1, round(days / 30))
        trends = profit_calc.get_profit_trends(months=trend_months)

        monthly = trends.get('monthly', [])
        chart_labels = [m.get('label') or m.get('month') for m in monthly]
        chart_revenue = [float(m.get('revenue', 0) or 0) for m in monthly]
        chart_profit = [float(m.get('net_profit', 0) or 0) for m in monthly]
        chart_orders = [int(m.get('order_count', 0) or 0) for m in monthly]

        low_stock = Product.query.filter(
            Product.user_id == current_user.id,
            Product.is_active == True,  # noqa: E712
            Product.current_stock <= Product.reorder_level
        ).order_by(Product.name).limit(10).all()

        alerts = [{
            'type': 'warning',
            'message': f"Low stock: {p.name} ({float(p.current_stock or 0):.2f} left)"
        } for p in low_stock]

        return {
            'period': period,
            'kpi': {
                'total_revenue': float(revenue),
                'revenue_growth': _growth(float(revenue), float(prev_revenue)),
                'total_orders': int(orders_count),
                'orders_growth': _growth(float(orders_count), float(prev_orders)),
                'net_profit': float(profit_summary.get('net_profit', 0) or 0),
                'profit_margin': float(profit_summary.get('net_margin', 0) or 0),
                'total_customers': int(customer_count),
                'customer_growth': 0.0,
            },
            'charts': {
                'labels': chart_labels,
                'revenue': chart_revenue,
                'profit': chart_profit,
                'orders': chart_orders,
            },
            'alerts': alerts
        }


@ns.route('/drilldown/<string:metric>')
class DashboardDrillDown(Resource):
    method_decorators = [login_required]

    def get(self, metric: str):
        start_date, end_date = _date_window()
        metric = (metric or '').lower()

        if metric == 'revenue':
            category_rows = db.session.query(
                Product.category,
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).label('revenue')
            ).join(OrderItem, OrderItem.product_id == Product.id).join(Order, Order.id == OrderItem.order_id).filter(
                Order.user_id == current_user.id,
                Order.status == Order.STATUS_COMPLETED,
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(Product.category).order_by(func.sum(OrderItem.subtotal).desc()).all()

            top_products = db.session.query(
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold'),
                func.coalesce(func.sum(OrderItem.subtotal), 0.0).label('revenue')
            ).join(OrderItem, OrderItem.product_id == Product.id).join(Order, Order.id == OrderItem.order_id).filter(
                Order.user_id == current_user.id,
                Order.status == Order.STATUS_COMPLETED,
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(Product.id, Product.name).order_by(func.sum(OrderItem.subtotal).desc()).limit(10).all()

            return {
                'categories': [
                    {'category': (row.category or 'Uncategorized'), 'revenue': float(row.revenue or 0)}
                    for row in category_rows
                ],
                'top_products': [
                    {'name': row.name, 'units_sold': float(row.units_sold or 0), 'revenue': float(row.revenue or 0)}
                    for row in top_products
                ]
            }

        if metric == 'orders':
            status_rows = db.session.query(
                Order.status,
                func.count(Order.id).label('count')
            ).filter(
                Order.user_id == current_user.id,
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).group_by(Order.status).all()

            recent = db.session.query(Order).filter(
                Order.user_id == current_user.id
            ).order_by(Order.order_date.desc()).limit(20).all()

            return {
                'status_breakdown': [{'status': row.status, 'count': int(row.count)} for row in status_rows],
                'recent_orders': [{
                    'id': row.id,
                    'order_number': row.order_number,
                    'status': row.status,
                    'total_amount': float(row.total_amount or 0),
                    'order_date': row.order_date.isoformat() if row.order_date else None,
                    'customer_id': row.customer_id
                } for row in recent]
            }

        if metric == 'profit':
            period, days = _resolve_period()
            months = max(1, round(days / 30))
            profit_calc = ProfitCalculator(current_user.id)
            summary = profit_calc.get_profit_summary(start_date=start_date, end_date=end_date)
            trends = profit_calc.get_profit_trends(months=months)
            return {'period': period, 'summary': summary, 'trends': trends}

        return {'message': f'Unsupported drilldown metric: {metric}'}, 400


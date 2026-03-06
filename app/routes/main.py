# app/routes/main.py

from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from app.services.profit_calculator import ProfitCalculator
from app.services.business_metrics import BusinessMetrics
from app.utils.decorators import track_performance, rate_limit
from app.models import Product, InventoryLot, OrderItem
from app.validators import validate_pagination
from app.security import SecurityUtils
from app.extensions import db
from sqlalchemy import func
from app.routes.api_utils import APIResponse
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

DEFAULT_PERIOD: str = '6m'
VALID_PERIODS: dict[str, int] = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}

@main_bp.route('/')
def index():
    """Render public About page for prospects and new users."""
    return render_template('index.html')

@main_bp.route('/terms')
def terms():
    """Render the Terms of Service page."""
    return render_template('main/terms.html')

@main_bp.route('/privacy')
def privacy():
    """Render the Privacy Policy page."""
    return render_template('main/privacy.html')

@main_bp.route('/dashboard')
@login_required
@rate_limit(max_calls=30, period=60)  # 30 dashboard loads per minute
@track_performance('dashboard_load')
def dashboard():
    """Render main dashboard with key metrics and profit analysis.
    Only accessible to authenticated users."""
    try:
        # Get and validate period parameter
        period = request.args.get('period', DEFAULT_PERIOD)
        if period not in VALID_PERIODS:
            period = DEFAULT_PERIOD
            SecurityUtils.log_security_event('invalid_dashboard_period', {
                'user_id': current_user.id,
                'invalid_period': request.args.get('period'),
                'ip': request.remote_addr
            }, 'warning')
            
        # Validate pagination parameters for API endpoints
        # Validate pagination parameters for API endpoints (not used in dashboard, but validated)
        _pagination: dict[str, int] = validate_pagination(
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 20, type=int),
            max_per_page=50
        )
        
        # Get date range based on period
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=VALID_PERIODS[period])
        
        try:
            # Initialize services
            business_metrics = BusinessMetrics(user_id=current_user.id)
            profit_calculator = ProfitCalculator(current_user.id)
            
            # Get comprehensive business metrics for the selected period
            current_app.logger.info("Fetching business metrics...")
            metrics = business_metrics.get_financial_health(start_date=start_date, end_date=end_date)
            
            # Get product-focused metrics
            current_month = datetime.now(timezone.utc).strftime('%Y-%m')
            profit_data = profit_calculator.get_profit_summary(start_date=start_date, end_date=end_date) or {}
            
            # Get trends data
            current_app.logger.info("Fetching profit trends...")
            trend_months = max(1, round(VALID_PERIODS[period] / 30))
            profit_trends = profit_calculator.get_profit_trends(months=trend_months) or {'monthly': []}
            cash_flow_trends = business_metrics.get_cash_flow_trends(months=trend_months)
            
            # Get top products
            current_app.logger.info("Fetching top products...")
            top_products_raw = profit_calculator.get_product_profitability(
                start_date=start_date,
                end_date=end_date,
                limit=5
            ) or []
            top_products = sorted(
                top_products_raw,
                key=lambda product: float(product.get('profit', 0) or 0),
                reverse=True
            )[:5]

            # Get alerts
            current_app.logger.info("Fetching product alerts...")
            alerts = get_product_alerts(current_user.id) or []

            # Prepare context with enhanced metrics
            chart_data = _prepare_chart_data(
                metrics,
                profit_trends,
                top_products,
                cash_flow_trends
            )
            latest_label = chart_data.pop('latest_label', None)
            chart_data.pop('window_labels', None)
            briefs = _build_dashboard_briefs(
                metrics,
                profit_trends,
                cash_flow_trends,
                top_products,
                latest_label=latest_label
            )
            context = {
                'metrics': metrics,
                'profit_data': profit_data,
                'profit_trends': profit_trends,
                'top_products': top_products,
                'alerts': alerts,
                'period': period,
                'valid_periods': VALID_PERIODS,
                'current_month': current_month,
                'now': datetime.now(timezone.utc),
                'chart_data': chart_data,
                'briefs': briefs,
                'cash_flow_trends': cash_flow_trends
            }
            
            current_app.logger.info("Rendering dashboard template...")
            return render_template('main/dashboard.html', **context)
            
        except Exception as e:
            current_app.logger.error(f"Error loading dashboard data: {str(e)}", exc_info=True)
            SecurityUtils.log_security_event('dashboard_load_error', {
                'user_id': current_user.id,
                'error': str(e),
                'ip': request.remote_addr
            }, 'error')
            return render_template('main/dashboard.html', **get_default_dashboard_context(period))
            
    except Exception as e:
        current_app.logger.critical(f"Critical error in dashboard route: {str(e)}", exc_info=True)
        flash('A critical error occurred. Please try again later.', 'error')
        return redirect(url_for('main.index'))

from typing import Any, Dict, List, Optional

def _prepare_chart_data(
    metrics: dict[str, Any],
    profit_trends: dict[str, Any],
    top_products: Optional[list[dict[str, Any]]] = None,
    cash_flow_trends: Optional[list[dict[str, Any]]] = None
) -> dict[str, Any]:
    """Prepare chart data for the dashboard."""
    # Prepare monthly data for charts
    monthly_data = profit_trends.get('monthly', [])

    # If no real data, provide sample data for demonstration
    if not monthly_data:
        current_date = datetime.now()
        monthly_data = []
        for i in range(6):
            month_date = current_date - timedelta(days=30 * (5 - i))
            monthly_data.append({
                'month': month_date.strftime('%Y-%m'),
                'revenue': 10000 + (i * 2000),  # Sample revenue
                'gross_profit': 3000 + (i * 600),  # Sample gross profit
                'gross_margin': 30.0,  # Sample margin
                'net_margin': 20.0,  # Sample net margin
                'label': month_date.strftime('%b %Y')
            })

    window_labels = [m.get('label', m.get('month', '')) for m in monthly_data]
    latest_label = window_labels[-1] if window_labels else ''

    # Safely get nested values with defaults
    expenses_metrics = metrics.get('expenses', {})
    expense_breakdown = expenses_metrics.get('expense_breakdown', []) or []
    expense_categories = expenses_metrics.get('expense_categories', {}) or {}
    total_expenses = float(expenses_metrics.get('total_expenses', 0) or 0)
    cash_flow = metrics.get('cash_flow', {})

    expense_labels = []
    expense_values = []

    if expense_breakdown:
        for item in expense_breakdown:
            category = str(item.get('category', 'Uncategorized') or 'Uncategorized')
            amount = float(item.get('amount', 0) or 0)
            if amount > 0:
                expense_labels.append(category)
                expense_values.append(amount)
    elif expense_categories:
        for category, amount in expense_categories.items():
            value = float(amount or 0)
            if value > 0:
                expense_labels.append(str(category).replace('_', ' ').title())
                expense_values.append(value)

    if not expense_values and total_expenses > 0:
        expense_labels = ['Uncategorized']
        expense_values = [total_expenses]
    elif not expense_values:
        # Provide sample expense data
        expense_labels = ['Rent', 'Utilities', 'Salaries', 'Marketing', 'Other']
        expense_values = [2000, 500, 3000, 1000, 800]

    top_products = top_products or []
    top_product_labels = [str(product.get('name', 'Unknown')) for product in top_products[:8]]
    top_product_profits = [float(product.get('profit', 0) or 0) for product in top_products[:8]]

    # If no top products data, provide sample data
    if not top_product_labels:
        top_product_labels = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
        top_product_profits = [1500, 1200, 800, 600, 400]

    cash_flow_trends = cash_flow_trends or []
    cashflow_labels = [entry.get('label', '') for entry in cash_flow_trends]

    if not cashflow_labels:
        cashflow_labels = [m.get('label', m.get('month', '')) for m in monthly_data]
    if not cashflow_labels:
        cashflow_labels = ['Month 1']

    def _trend_series(key: str) -> list[float]:
        if cash_flow_trends:
            return [float(entry.get(key, 0) or 0) for entry in cash_flow_trends]
        return [0.0] * len(cashflow_labels)

    cashflow_datasets = [
        {
            'label': 'Cash In',
            'data': _trend_series('cash_in'),
            'borderColor': '#16a34a',
            'backgroundColor': 'rgba(16, 163, 74, 0.12)',
            'tension': 0.35
        },
        {
            'label': 'Cash Out',
            'data': _trend_series('cash_out'),
            'borderColor': '#dc2626',
            'borderDash': [5, 5],
            'backgroundColor': 'rgba(220, 38, 38, 0.12)',
            'tension': 0.35
        },
        {
            'label': 'Operating Cash Flow',
            'data': _trend_series('operating_cash_flow'),
            'borderColor': '#0d6efd',
            'backgroundColor': 'rgba(13, 110, 253, 0.15)',
            'tension': 0.4,
            'fill': 'origin'
        }
    ]

    return {
        'revenue': {
            'labels': [m.get('label', m.get('month', '')) for m in monthly_data],
            'datasets': [{
                'label': 'Revenue',
                'data': [m.get('revenue', 0) for m in monthly_data],
                'borderColor': '#3F4E4F',
                'backgroundColor': 'rgba(63, 78, 79, 0.1)'
            }]
        },
        'profitability': {
            'labels': [m.get('label', m.get('month', '')) for m in monthly_data],
            'datasets': [{
                'label': 'Gross Margin',
                'data': [m.get('gross_margin', 0) for m in monthly_data],
                'borderColor': '#A27B5C',
                'backgroundColor': 'rgba(162, 123, 92, 0.1)'
            }, {
                'label': 'Net Margin',
                'data': [m.get('net_margin', 0) for m in monthly_data],
                'borderColor': '#DCD7C9',
                'backgroundColor': 'rgba(220, 215, 201, 0.1)'
            }]
        },
        'expenses': {
            'labels': expense_labels,
            'datasets': [{
                'data': expense_values,
                'backgroundColor': [
                    '#3F4E4F', '#A27B5C', '#DCD7C9', '#2C3639',
                    '#5F6B6D', '#BFA18F', '#E8E4DC', '#4D5B5C'
                ]
            }]
        },
        'cash_flow': {
            'labels': ['Cash In', 'Cash Out', 'Net Cash Flow'],
            'datasets': [{
                'data': [
                    cash_flow.get('cash_in', 0) or 15000,  # Fallback sample data
                    cash_flow.get('cash_out', 0) or 8000,  # Fallback sample data
                    cash_flow.get('operating_cash_flow', 0) or 7000  # Fallback sample data
                ],
                'backgroundColor': [
                    'rgba(63, 78, 79, 0.7)',  # Dark green for cash in
                    'rgba(220, 53, 69, 0.7)',  # Red for cash out
                    'rgba(25, 135, 84, 0.7)'   # Green for net cash flow
                ]
            }]
        },
        'top_products': {
            'labels': top_product_labels,
            'datasets': [{
                'data': top_product_profits
            }]
        },
        'cashflow_trend': {
            'labels': cashflow_labels,
            'datasets': cashflow_datasets
        },
        'window_labels': window_labels,
        'latest_label': latest_label
    }


def _build_dashboard_briefs(
    metrics: dict[str, Any],
    profit_trends: dict[str, Any],
    cash_flow_trends: Optional[list[dict[str, Any]]] = None,
    top_products: Optional[list[dict[str, Any]]] = None,
    latest_label: Optional[str] = None
) -> list[dict[str, Any]]:
    """Compile brief summaries that align with the dashboard charts."""
    revenue = metrics.get('revenue', {})
    profitability = metrics.get('profitability', {})
    cash_flow = metrics.get('cash_flow', {})
    cash_flow_trends = cash_flow_trends or []
    top_products = top_products or []

    latest_cash = cash_flow_trends[-1] if cash_flow_trends else {}
    previous_cash = cash_flow_trends[-2] if len(cash_flow_trends) > 1 else latest_cash
    cash_delta = float(latest_cash.get('operating_cash_flow', 0) or 0) - float(previous_cash.get('operating_cash_flow', 0) or 0)

    latest_period_label = (
        latest_label
        or (
            profit_trends.get('monthly', [])[-1].get('label')
            if profit_trends.get('monthly')
            else None
        )
        or (profit_trends.get('months', [])[-1] if profit_trends.get('months') else None)
        or latest_cash.get('label', '')
    )
    top_product = top_products[0] if top_products else {}
    top_product_name = top_product.get('name') or 'Top product'

    return [
        {
            'id': 'revenue-brief',
            'title': 'Revenue Momentum',
            'value': revenue.get('total_revenue', 0),
            'unit': '$',
            'detail': f"Avg order ${revenue.get('average_order_value', 0):,.0f}",
            'trend': revenue.get('revenue_growth', 0),
            'trend_label': 'vs previous period',
            'positive': revenue.get('revenue_growth', 0) >= 0,
            'icon': 'fas fa-chart-line',
            'chart_target': 'revenueChart',
            'badge': latest_period_label or 'Latest period',
            'trend_format': 'percent'
        },
        {
            'id': 'profitability-brief',
            'title': 'Profitability Pulse',
            'value': profitability.get('net_profit', 0),
            'unit': '$',
            'detail': f"{profitability.get('net_margin', 0):.1f}% net margin",
            'trend': profitability.get('net_margin', 0),
            'trend_label': 'Net margin',
            'positive': profitability.get('net_margin', 0) >= 0,
            'icon': 'fas fa-percent',
            'chart_target': 'profitabilityChart',
            'badge': 'Margins',
            'trend_format': 'percent'
        },
        {
            'id': 'cashflow-brief',
            'title': 'Cash Flow Trajectory',
            'value': cash_flow.get('operating_cash_flow', 0),
            'unit': '$',
            'detail': f"{cash_flow.get('runway', 0):.1f} mo runway",
            'trend': cash_delta,
            'trend_label': 'vs prior month',
            'positive': cash_delta >= 0,
            'icon': 'fas fa-wallet',
            'chart_target': 'cashFlowTrendChart',
            'badge': 'Cash health',
            'trend_format': 'currency'
        },
        {
            'id': 'top-product-brief',
            'title': 'Top Product Insight',
            'value': float(top_product.get('profit', 0) or 0),
            'unit': '$',
            'detail': top_product_name,
            'trend': float(top_product.get('margin', 0) or 0),
            'trend_label': 'Margin',
            'positive': float(top_product.get('margin', 0) or 0) >= 0,
            'icon': 'fas fa-boxes-stacked',
            'chart_target': 'topProductsChart',
            'badge': 'By profit',
            'trend_format': 'percent'
        }
    ]

def get_default_dashboard_context(period: str) -> dict[str, Any]:
    """Return default context for dashboard when there's an error."""
    now = datetime.now(timezone.utc)
    current_month = now.strftime('%Y-%m')

    # Generate default monthly data
    monthly: list[dict[str, Any]] = [{
        'month': (now - timedelta(days=30*i)).strftime('%Y-%m'),
        'revenue': 0,
        'profit': 0,
        'gross_profit': 0,
        'operating_profit': 0,
        'gross_margin': 0,
        'net_margin': 0,
        'label': (now - timedelta(days=30*i)).strftime('%b %Y')
    } for i in range(6, 0, -1)]

    metrics = {
        'revenue': {
            'total_revenue': 0.0,
            'revenue_growth': 0.0,
            'revenue_by_category': {},
            'average_order_value': 0.0,
            'recurring_revenue': 0.0,
            'customer_count': 0,
            'source_breakdown': {
                'manual': {'revenue': 0.0, 'orders': 0, 'customers': 0},
                'storefront': {'revenue': 0.0, 'orders': 0, 'customers': 0},
                'combined': {'revenue': 0.0, 'orders': 0, 'customers': 0}
            }
        },
        'expenses': {
            'total_expenses': 0.0,
            'expenses_by_category': {},
            'expense_breakdown': []
        },
        'profitability': {
            'gross_profit': 0.0,
            'gross_margin': 0.0,
            'operating_profit': 0.0,
            'operating_margin': 0.0,
            'net_profit': 0.0,
            'net_margin': 0.0,
            'roi': 0.0,
            'break_even_point': 0.0,
            'source_breakdown': {
                'manual': {
                    'revenue': 0.0,
                    'subtotal': 0.0,
                    'tax': 0.0,
                    'orders': 0,
                    'avg_order_value': 0.0,
                    'gross_profit': 0.0,
                    'gross_margin': 0.0,
                    'allocated_overhead': 0.0,
                    'net_profit': 0.0,
                    'net_margin': 0.0
                },
                'storefront': {
                    'revenue': 0.0,
                    'subtotal': 0.0,
                    'tax': 0.0,
                    'orders': 0,
                    'avg_order_value': 0.0,
                    'gross_profit': 0.0,
                    'gross_margin': 0.0,
                    'allocated_overhead': 0.0,
                    'net_profit': 0.0,
                    'net_margin': 0.0
                },
                'combined': {
                    'revenue': 0.0,
                    'subtotal': 0.0,
                    'tax': 0.0,
                    'orders': 0,
                    'avg_order_value': 0.0,
                    'gross_profit': 0.0,
                    'gross_margin': 0.0,
                    'allocated_overhead': 0.0,
                    'net_profit': 0.0,
                    'net_margin': 0.0
                }
            }
        },
        'cash_flow': {
            'operating_cash_flow': 0.0,
            'cash_in': 0.0,
            'cash_out': 0.0,
            'cash_burn_rate': 0.0,
            'runway': 0.0
        },
        'working_capital': {
            'current_assets': 0.0,
            'current_liabilities': 0.0,
            'working_capital': 0.0,
            'current_ratio': 0.0,
            'quick_ratio': 0.0,
            'inventory_turnover': 0.0,
            'days_sales_outstanding': 0.0
        },
        'metrics_date': current_month
    }

    profit_trends = {
        'months': [m['label'] for m in monthly],
        'revenue': [0] * len(monthly),
        'gross_profit': [0] * len(monthly),
        'operating_profit': [0] * len(monthly),
        'net_profit': [0] * len(monthly),
        'gross_margin': [0] * len(monthly),
        'operating_margin': [0] * len(monthly),
        'net_margin': [0] * len(monthly),
        'monthly': monthly
    }

    cash_flow_trends = [{
        'label': month['label'],
        'month': month['month'],
        'cash_in': 0.0,
        'cash_out': 0.0,
        'operating_cash_flow': 0.0
    } for month in monthly]

    top_products: list[dict[str, Any]] = []

    chart_data = _prepare_chart_data(metrics, profit_trends, top_products, cash_flow_trends)
    briefs = _build_dashboard_briefs(metrics, profit_trends, cash_flow_trends, top_products)

    return {
        'metrics': metrics,
        'profit_data': {
            'revenue': 0.0,
            'cogs': 0.0,
            'gross_profit': 0.0,
            'gross_margin': 0.0,
            'operating_expenses': 0.0,
            'operating_profit': 0.0,
            'operating_margin': 0.0,
            'net_profit': 0.0,
            'net_margin': 0.0,
            'expense_categories': {
                'fixed': 0.0,
                'variable': 0.0,
                'semi_variable': 0.0
            },
            'direct_costs': 0.0,
            'allocated_shared_costs': 0.0,
            'total_operating_expenses': 0.0,
            'other_expenses': 0.0,
            'profit': 0.0,
            'margin': 0.0
        },
        'profit_trends': profit_trends,
        'top_products': top_products,
        'alerts': [],
        'period': period,
        'valid_periods': {
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365
        },
        'current_month': current_month,
        'now': now,
        'chart_data': chart_data,
        'briefs': briefs,
        'cash_flow_trends': cash_flow_trends
    }

@main_bp.route('/api/profit/trends')
@login_required
@rate_limit(max_calls=20, period=60)
def profit_trends() -> Any:
    """API endpoint to get profit trends data with security validation."""
    try:
        # Validate and sanitize input parameters
        months = request.args.get('months', 12, type=int)
        if months < 1 or months > 24:
            SecurityUtils.log_security_event('invalid_trends_months', {
                'user_id': current_user.id,
                'months': months,
                'ip': request.remote_addr
            }, 'warning')
            return APIResponse.error(
                message="Months parameter must be between 1 and 24",
                status_code=400,
                error_code='INVALID_PARAMETER'
            )
        
        profit_calculator = ProfitCalculator(current_user.id)
        trends = profit_calculator.get_profit_trends(months=months)
        
        SecurityUtils.log_security_event('profit_trends_access', {
                'user_id': current_user.id,
                'months': months,
                'ip': request.remote_addr
            }, 'info')
        
        return APIResponse.success(data=trends, message="Profit trends retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting profit trends: {str(e)}", exc_info=True)
        SecurityUtils.log_security_event('profit_trends_error', {
            'user_id': current_user.id,
            'error': str(e),
            'ip': request.remote_addr
        }, 'error')
        return APIResponse.error(
            message="Failed to load profit trends",
            status_code=500,
            error_code='DATA_LOAD_ERROR'
        )

@main_bp.route('/api/profit/products')
@login_required
@rate_limit(max_calls=20, period=60)
def product_profitability() -> Any:
    """API endpoint to get product profitability data with security validation."""
    try:
        # Validate and sanitize input parameters
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        
        if limit < 1 or limit > 50:
            SecurityUtils.log_security_event('invalid_profitability_limit', {
                'user_id': current_user.id,
                'limit': limit,
                'ip': request.remote_addr
            }, 'warning')
            return APIResponse.error(
                message="Limit must be between 1 and 50",
                status_code=400,
                error_code='INVALID_PARAMETER'
            )
        
        if days < 1 or days > 365:
            SecurityUtils.log_security_event('invalid_profitability_days', {
                'user_id': current_user.id,
                'days': days,
                'ip': request.remote_addr
            }, 'warning')
            return APIResponse.error(
                message="Days must be between 1 and 365",
                status_code=400,
                error_code='INVALID_PARAMETER'
            )
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        profit_calculator = ProfitCalculator(current_user.id)
        products = profit_calculator.get_product_profitability(
            start_date=start_date,
            end_date=datetime.now(timezone.utc),
            limit=limit
        )
        
        SecurityUtils.log_security_event('product_profitability_access', {
            'user_id': current_user.id,
            'limit': limit,
            'days': days,
            'ip': request.remote_addr
        }, 'info')
        
        return APIResponse.success(data=products, message="Product profitability data retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting product profitability: {str(e)}", exc_info=True)
        SecurityUtils.log_security_event('product_profitability_error', {
            'user_id': current_user.id,
            'error': str(e),
            'ip': request.remote_addr
        }, 'error')
        return APIResponse.error(
            message="Failed to load product profitability data",
            status_code=500,
            error_code='DATA_LOAD_ERROR'
        )

@main_bp.route('/api/profit/summary')
@login_required
def profit_summary() -> Any:
    """API endpoint to get profit summary for a specific period."""
    try:
        profit_calculator = ProfitCalculator(current_user.id)
        
        # Get date range from query params or use current month
        year_month = request.args.get('month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if year_month:
            # Get summary for specific month
            profit_data = profit_calculator.get_profit_summary(year_month=year_month)
        elif start_date and end_date:
            # Get summary for custom date range
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            profit_data = profit_calculator.get_profit_summary(start_date=start, end_date=end)
        else:
            # Default to current month
            profit_data = profit_calculator.get_profit_summary()
        
        return jsonify(profit_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting profit summary: {str(e)}")
        return jsonify({"error": "Failed to load profit summary"}), 500

@main_bp.route('/api/dashboard/data')
@login_required
def get_dashboard_data() -> Any:
    period = request.args.get('period', '6m')
    
    try:
        # Initialize services
        profit_calculator = ProfitCalculator(current_user.id)
        
        days = VALID_PERIODS.get(period, VALID_PERIODS[DEFAULT_PERIOD])
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get profit summary for the current period
        profit_data = profit_calculator.get_profit_summary(start_date=start_date, end_date=end_date)
        
        # Get profit trends
        months = max(1, round(days / 30))
        profit_trends = profit_calculator.get_profit_trends(months=months)

        summary = {
            'revenue': profit_data.get('revenue', 0),
            'gross_profit': profit_data.get('gross_profit', 0),
            'gross_margin': profit_data.get('gross_margin', 0),
            'operating_profit': profit_data.get('operating_profit', 0),
            'operating_margin': profit_data.get('operating_margin', 0),
            'net_profit': profit_data.get('net_profit', 0),
            'net_margin': profit_data.get('net_margin', 0)
        }
        trends = {
            'months': profit_trends.get('months', []),
            'revenue': profit_trends.get('revenue', []),
            'gross_profit': profit_trends.get('gross_profit', []),
            'operating_profit': profit_trends.get('operating_profit', []),
            'net_profit': profit_trends.get('net_profit', []),
            'monthly': profit_trends.get('monthly', [])
        }

        # Keep both top-level and nested structure for backward compatibility.
        return jsonify({
            'status': 'success',
            'summary': summary,
            'trends': trends,
            'data': {
                'summary': summary,
                'chart_data': trends
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard_data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to load dashboard data'
        }), 500

from sqlalchemy.orm import Session

def get_product_alerts(user_id: int, session: Optional[Session] = None) -> list[dict[str, Any]]:
    local_session = False
    if session is None:
        session = db.session
        local_session = True

    try:
        alerts: list[dict[str, Any]] = []
        threshold_date = datetime.now(timezone.utc) + timedelta(days=30)

        # Low stock
        low_inventory = (
            session.query(
                Product.id,
                Product.name,
                Product.current_stock.label('current_stock'),
                Product.reorder_level
            )
            .filter(Product.user_id == user_id)
            .filter(Product.current_stock <= Product.reorder_level)
            .all()
        )

        for product in low_inventory:
            alerts.append({
                'type': 'low_stock',
                'product_id': product.id,
                'product_name': product.name,
                'current_stock': float(product.current_stock or 0),
                'reorder_level': float(product.reorder_level or 0),
                'message': f"Low stock: {product.name} is below reorder level"
            })

        # Expiring inventory
        # First, get all lots that have expiration dates
        all_lots = session.query(InventoryLot).join(Product).filter(
            Product.user_id == user_id,
            InventoryLot.expiration_date.isnot(None),
            InventoryLot.expiration_date <= threshold_date
        ).all()

        # Filter out lots that have been completely sold
        expiring_lots = []
        for lot in all_lots:
            # Calculate remaining quantity
            sold_quantity = session.query(func.coalesce(func.sum(OrderItem.quantity), 0)).filter(
                OrderItem.lot_id == lot.id
            ).scalar() or 0

            remaining_quantity = lot.quantity_received - sold_quantity

            if remaining_quantity > 0:
                lot.quantity_remaining = remaining_quantity  # Add dynamic attribute
                expiring_lots.append(lot)

        for lot in expiring_lots:
            days_until_expiry = (lot.expiration_date - datetime.now(timezone.utc).date()).days
            alerts.append({
                'type': 'expiring_soon',
                'product_id': lot.product_id,
                'lot_id': lot.id,
                'product_name': lot.product.name,
                'expiration_date': lot.expiration_date.strftime('%Y-%m-%d'),
                'days_until_expiry': days_until_expiry,
                'quantity': lot.quantity_remaining,
                'message': f"Expiring soon: {lot.quantity_remaining} units of {lot.product.name} "
                           f"expire in {days_until_expiry} days"
            })

        return alerts

    except Exception as e:
        logger.error(f"Error getting product alerts for user {user_id}: {e}", exc_info=True)
        return []

    finally:
        if local_session:
            session.close()

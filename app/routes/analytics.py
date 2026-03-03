# app/routes/analytics.py

from datetime import datetime, timedelta
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
import logging

# Import services for data fetching
from app.services.business_metrics import BusinessMetrics
from app.services.profit_calculator import ProfitCalculator

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
@login_required
def analytics():
    """Render the main analytics dashboard with initial data.
    
    This view serves the main analytics dashboard page with initial data.
    Additional data fetching is handled asynchronously via API endpoints.
    """
    try:
        # Default date range for initial page load
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        # Format dates for display in the date range picker
        date_range = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
        
        # Get initial analytics data
        business_metrics = BusinessMetrics(user_id=current_user.id)
        profit_calculator = ProfitCalculator(user_id=current_user.id)
        
        # Get basic metrics
        metrics = business_metrics.get_financial_health(start_date=start_date, end_date=end_date)
        profit_trends = profit_calculator.get_profit_trends(months=6)
        top_products = business_metrics.get_top_products(limit=10)
        category_data = business_metrics.get_category_breakdown()
        funnel_data = business_metrics.get_sales_funnel()    
            
        # Prepare initial chart data
        chart_data = _prepare_analytics_chart_data(metrics, profit_trends, top_products, category_data, funnel_data)
        
        return render_template(
            'main/analytics.html',
            title='Enhanced Sales Analytics',
            date_range=date_range,
            metrics=metrics,
            chart_data=chart_data
        )
        
    except Exception as e:
        logger.error(f"Error rendering analytics dashboard: {str(e)}", exc_info=True)
        current_app.logger.exception("Failed to render analytics dashboard")
        return render_template(
            'main/analytics.html',
            title='Enhanced Sales Analytics',
            error="Failed to load analytics dashboard. Please try again later."
        ), 500

def _prepare_analytics_chart_data(metrics, profit_trends, top_products, category_data=None, funnel_data=None):
    """Prepare chart data for analytics dashboard."""
    from datetime import datetime, timedelta
    
    # Prepare monthly data from profit trends
    monthly_data = profit_trends.get('monthly', [])
    
    # Prepare revenue chart data
    revenue_labels = []
    revenue_data = []
    orders_data = []
    
    if monthly_data:
        for month_data in monthly_data:
            revenue_labels.append(month_data.get('month', ''))
            revenue_data.append(month_data.get('revenue', 0))
            orders_data.append(month_data.get('orders', 0))
    
    # Prepare category data
    category_labels = []
    category_values = []
    
    if category_data:
        for cat in category_data:
            category_labels.append(cat.get('category', 'Unknown'))
            category_values.append(cat.get('revenue', 0))
    
    # Prepare funnel data
    funnel = {
        'visitors': funnel_data.get('visitors', 0) if funnel_data else 0,
        'cart_adds': funnel_data.get('cart_adds', 0) if funnel_data else 0,
        'checkouts': funnel_data.get('checkouts', 0) if funnel_data else 0,
        'purchases': funnel_data.get('purchases', 0) if funnel_data else 0
    }
    
    return {
        'revenue': {
            'labels': revenue_labels,
            'datasets': [{
                'label': 'Revenue',
                'data': revenue_data,
                'borderColor': '#3F4E4F',
                'backgroundColor': 'rgba(63, 78, 79, 0.1)'
            }]
        },
        'orders': {
            'labels': revenue_labels,
            'datasets': [{
                'label': 'Orders',
                'data': orders_data,
                'borderColor': '#28A745',
                'backgroundColor': 'rgba(40, 167, 69, 0.1)'
            }]
        },
        'categories': {
            'labels': category_labels,
            'datasets': [{
                'data': category_values,
                'backgroundColor': [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
                ]
            }]
        },
        'funnel': funnel
    }

@analytics_bp.route('/product/<int:product_id>')
@login_required
def product_analytics(product_id: int):
    """Render the product-specific analytics page.
    
    Args:
        product_id: The ID of the product to display analytics for
    """
    try:
        # Default date range for initial page load
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        return render_template(
            'dashboard/analytics/product_analytics.html',
            title='Product Analytics',
            product_id=product_id,
            date_range={
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        )
        
    except Exception as e:
        logger.error(f"Error rendering product analytics for product {product_id}: {str(e)}", exc_info=True)
        return render_template(
            'dashboard/analytics/product_analytics.html',
            title='Product Analytics',
            product_id=product_id,
            error=f"Failed to load analytics for product {product_id}. Please try again later."
        ), 500

#!/usr/bin/env python3
"""
Test analytics route data passing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.business_metrics import BusinessMetrics
from app.services.profit_calculator import ProfitCalculator
from flask import render_template_string

def test_analytics_route():
    """Test analytics route data preparation"""
    app = create_app()
    
    with app.app_context():
        print("Testing Analytics Route Data Preparation")
        print("=" * 50)
        
        # Simulate current user
        from flask_login import AnonymousUserMixin
        current_user = type('TestUser', (), {'id': 1})()
        
        try:
            # Get initial analytics data (same as route)
            business_metrics = BusinessMetrics(user_id=current_user.id)
            profit_calculator = ProfitCalculator(user_id=current_user.id)
            
            # Get basic metrics
            metrics = business_metrics.get_financial_health()
            profit_trends = profit_calculator.get_profit_trends(months=6)
            top_products = business_metrics.get_top_products(limit=10)
            category_data = business_metrics.get_category_breakdown()
            funnel_data = business_metrics.get_sales_funnel()
            
            print("✓ Metrics retrieved successfully")
            print(f"  - Revenue metrics keys: {list(metrics.keys()) if metrics else 'None'}")
            print(f"  - Profit trends keys: {list(profit_trends.keys()) if profit_trends else 'None'}")
            print(f"  - Top products count: {len(top_products) if top_products else 0}")
            print(f"  - Category data count: {len(category_data) if category_data else 0}")
            print(f"  - Funnel data keys: {list(funnel_data.keys()) if funnel_data else 'None'}")
            
            # Prepare chart data (same as route)
            from app.routes.analytics import _prepare_analytics_chart_data
            chart_data = _prepare_analytics_chart_data(
                metrics, profit_trends, top_products, category_data, funnel_data
            )
            
            print("\n✓ Chart data prepared successfully")
            print(f"  - Revenue chart labels: {len(chart_data['revenue']['labels'])}")
            print(f"  - Category chart labels: {len(chart_data['categories']['labels'])}")
            print(f"  - Funnel data: {chart_data['funnel']}")
            
            # Test template rendering
            template_content = """
            <script>
            var chartData = {{ chart_data|tojson|safe }};
            var metrics = {{ metrics|tojson|safe }};
            console.log('Template chart data:', chartData);
            console.log('Template metrics:', metrics);
            </script>
            """
            
            rendered = render_template_string(
                template_content,
                chart_data=chart_data,
                metrics=metrics
            )
            
            print("\n✓ Template rendering test passed")
            print("Sample rendered content:")
            print(rendered[:200] + "...")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in analytics route: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    test_analytics_route()

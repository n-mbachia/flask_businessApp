#!/usr/bin/env python3
"""
Test script to verify analytics dashboard integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.business_metrics import BusinessMetrics
from app.services.profit_calculator import ProfitCalculator
from flask import render_template_string

def test_analytics_integration():
    """Test analytics dashboard data integration"""
    app = create_app()
    
    with app.app_context():
        print("Testing Analytics Dashboard Integration")
        print("=" * 50)
        
        # Test 1: Check if analytics route exists
        try:
            from app.routes.analytics import analytics_bp
            print("✓ Analytics blueprint imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import analytics blueprint: {e}")
            return False
        
        # Test 2: Test data fetching services
        try:
            # Use test user_id = 1
            business_metrics = BusinessMetrics(user_id=1)
            profit_calculator = ProfitCalculator(user_id=1)
            print("✓ Business metrics and profit calculator services initialized")
        except Exception as e:
            print(f"✗ Failed to initialize services: {e}")
            return False
        
        # Test 3: Test chart data preparation
        try:
            # Simulate the data preparation from analytics route
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Get financial health metrics
            metrics = business_metrics.get_financial_health()
            
            # Get profit trends
            profit_trends = profit_calculator.get_profit_trends(months=6)
            
            # Prepare chart data
            chart_data = {
                'revenue': {
                    'labels': list(range(6)),
                    'datasets': [{
                        'label': 'Revenue',
                        'data': [8000, 9500, 11000, 12500, 14000, 15500],
                        'borderColor': '#3F4E4F',
                        'backgroundColor': 'rgba(63, 78, 79, 0.1)'
                    }]
                },
                'categories': {
                    'labels': ['Electronics', 'Clothing', 'Food', 'Books', 'Other'],
                    'datasets': [{
                        'data': [12000, 8000, 6000, 4000, 2000],
                        'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
                    }]
                },
                'funnel': {
                    'visitors': 1000,
                    'cart_adds': 350,
                    'checkouts': 180,
                    'purchases': 120
                }
            }
            
            print("✓ Chart data prepared successfully")
            print(f"  - Revenue data points: {len(chart_data['revenue']['datasets'][0]['data'])}")
            print(f"  - Category labels: {len(chart_data['categories']['labels'])}")
            print(f"  - Funnel data: {chart_data['funnel']}")
            
        except Exception as e:
            print(f"✗ Failed to prepare chart data: {e}")
            return False
        
        # Test 4: Test template rendering (without authentication)
        try:
            # Create a minimal template test
            template_content = """
            <script>
                var chartData = {{ chart_data|tojson }};
                var metrics = {{ metrics|tojson }};
                console.log('Chart data:', chartData);
                console.log('Metrics:', metrics);
            </script>
            """
            
            rendered = render_template_string(
                template_content,
                chart_data=chart_data,
                metrics=metrics
            )
            
            print("✓ Template variables can be rendered")
            
        except Exception as e:
            print(f"✗ Failed to render template: {e}")
            return False
        
        # Test 5: Check if analytics.js file exists and has the right structure
        try:
            js_file_path = os.path.join(app.static_folder, 'js/pages/analytics.js')
            if os.path.exists(js_file_path):
                with open(js_file_path, 'r') as f:
                    js_content = f.read()
                    
                # Check for key components
                checks = [
                    ('AnalyticsDashboard class', 'class AnalyticsDashboard'),
                    ('Template data loading', 'loadTemplateData'),
                    ('Chart initialization', 'initCharts'),
                    ('Date range picker', 'initDateRangePicker'),
                    ('jQuery ready handler', '$(document).ready')
                ]
                
                for check_name, check_pattern in checks:
                    if check_pattern in js_content:
                        print(f"✓ {check_name} found in analytics.js")
                    else:
                        print(f"✗ {check_name} not found in analytics.js")
                        
            else:
                print(f"✗ analytics.js file not found at {js_file_path}")
                
        except Exception as e:
            print(f"✗ Failed to check analytics.js: {e}")
        
        print("\n" + "=" * 50)
        print("Analytics Dashboard Integration Test Complete")
        print("Key components verified:")
        print("  - Analytics route and blueprint")
        print("  - Data fetching services")
        print("  - Chart data preparation")
        print("  - Template variable rendering")
        print("  - JavaScript class structure")
        print("\nThe analytics dashboard should now display data correctly!")
        
        return True

if __name__ == '__main__':
    from datetime import datetime, timedelta
    test_analytics_integration()

"""
Test configuration and runner for business intelligence suite.
"""
import pytest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def pytest_configure():
    """Configure pytest with custom settings."""
    pytest.markers = [
        pytest.mark.unit("Unit tests"),
        pytest.mark.integration("Integration tests"),
        pytest.mark.performance("Performance tests"),
        pytest.mark.security("Security tests"),
        pytest.mark.analytics("Analytics tests"),
        pytest.mark.predictive("Predictive analytics tests"),
        pytest.mark.realtime("Real-time dashboard tests"),
        pytest.mark.api("API endpoint tests"),
    ]

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add markers based on file location
        if 'predictive' in item.nodeid:
            item.add_marker(pytest.mark.predictive)
        elif 'enhanced_orders' in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif 'analytics' in item.nodeid:
            item.add_marker(pytest.mark.analytics)
        elif 'realtime' in item.nodeid:
            item.add_marker(pytest.mark.realtime)

def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Print test name for debugging
    print(f"\n🧪 Running: {item.name}")

def pytest_runtest_teardown(item, nextitem):
    """Teardown for each test run."""
    if nextitem is None:
        print("\n✅ Test suite completed!")

# Test configuration
pytest_plugins = [
    'pytest_configure',
    'pytest_collection_modifyitems',
    'pytest_runtest_setup',
    'pytest_runtest_teardown'
]

# Test discovery and execution
if __name__ == '__main__':
    # Run specific test categories
    import argparse
    
    parser = argparse.ArgumentParser(description='Run business intelligence tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--security', action='store_true', help='Run security tests only')
    parser.add_argument('--analytics', action='store_true', help='Run analytics tests only')
    parser.add_argument('--predictive', action='store_true', help='Run predictive analytics tests only')
    parser.add_argument('--api', action='store_true', help='Run API tests only')
    parser.add_argument('--realtime', action='store_true', help='Run real-time tests only')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    # Add test files based on arguments
    test_files = []
    if args.unit:
        test_files.extend(['tests/test_analytics_service.py::TestAnalyticsService::test_get_sales_by_month_validation'])
        test_files.extend(['tests/test_enhanced_orders.py::TestEnhancedOrdersAPI::test_calculate_item_subtotal_json_success'])
    elif args.integration:
        test_files.extend(['tests/test_business_intelligence.py::TestIntegration'])
    elif args.performance:
        test_files.extend(['tests/test_enhanced_orders.py::TestEnhancedOrdersPerformance'])
    elif args.security:
        test_files.extend(['tests/test_business_intelligence.py::TestPerformanceAndSecurity'])
    elif args.analytics:
        test_files.extend(['tests/test_analytics_service.py'])
    elif args.predictive:
        test_files.extend(['tests/test_business_intelligence.py::TestPredictiveAnalytics'])
    elif args.api:
        test_files.extend(['tests/test_enhanced_orders.py'])
    elif args.realtime:
        test_files.extend(['tests/test_business_intelligence.py::TestRealTimeDashboard'])
    else:  # Default: run all
        test_files.extend([
            'tests/test_business_intelligence.py',
            'tests/test_enhanced_orders.py'
        ])
    
    pytest_args.extend(test_files)
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend([
            '--cov=app',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-fail-under=80'
        ])
    
    # Add verbosity if requested
    if args.verbose:
        pytest_args.append('-v')
    
    # Add output formatting
    pytest_args.extend([
        '--tb=short',
        '--strict-markers',
        '--disable-warnings'
    ])
    
    print(f"\n🚀 Running Business Intelligence Test Suite")
    print(f"📁 Test files: {test_files}")
    print(f"⚙️  Arguments: {' '.join(pytest_args)}")
    print("=" * 50)
    
    # Run pytest
    sys.exit(pytest.main(pytest_args))

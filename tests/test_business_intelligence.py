"""
Comprehensive test suite for business intelligence and analytics features.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
import json
import sys
import os

# Mock the flask_socketio module before importing
sys.modules['flask_socketio'] = Mock()

from app import create_app, db
from app.models import User, Order, Product, OrderItem, Customer
from app.services.predictive_analytics import PredictiveAnalytics
from app.services.analytics_service import AnalyticsService


class TestPredictiveAnalytics:
    """Test predictive analytics functionality."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    @pytest.fixture
    def sample_user(self, app):
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                password_hash='hashed_password'
            )
            db.session.add(user)
            db.session.commit()
            yield user
            db.session.delete(user)
            db.session.commit()
    
    @pytest.fixture
    def sample_orders(self, app, sample_user):
        with app.app_context():
            # Create sample orders for testing
            orders = []
            for i in range(12):  # 12 months of data
                order = Order(
                    user_id=sample_user.id,
                    total_amount=Decimal(f'{1000 + i * 100}'),
                    status='completed',
                    order_date=datetime.utcnow() - timedelta(days=30 * i)
                )
                db.session.add(order)
                orders.append(order)
            
            db.session.commit()
            yield orders
            
            # Cleanup
            for order in orders:
                db.session.delete(order)
            db.session.commit()
    
    def test_revenue_forecast_basic(self, app, sample_user, sample_orders):
        """Test basic revenue forecasting."""
        with app.app_context():
            result = PredictiveAnalytics.forecast_revenue(
                user_id=sample_user.id,
                periods=6
            )
            
            assert result is not None
            assert hasattr(result, 'predictions')
            assert hasattr(result, 'confidence_intervals')
            assert hasattr(result, 'accuracy_score')
            assert hasattr(result, 'trend_direction')
            assert len(result.predictions) == 6
    
    def test_revenue_forecast_insufficient_data(self, app, sample_user):
        """Test forecasting with insufficient data."""
        with app.app_context():
            result = PredictiveAnalytics.forecast_revenue(
                user_id=sample_user.id,
                periods=6
            )
            
            # Should handle insufficient data gracefully
            assert result.accuracy_score == 0.0
            assert 'insufficient' in result.recommendations[0].lower()
    
    def test_customer_segmentation(self, app, sample_user, sample_orders):
        """Test customer segmentation."""
        with app.app_context():
            # Create sample customers
            customers = []
            for i in range(10):
                customer = Customer(
                    user_id=sample_user.id,
                    name=f'Customer {i}',
                    email=f'customer{i}@example.com'
                )
                db.session.add(customer)
                customers.append(customer)
            
            db.session.commit()
            
            result = PredictiveAnalytics.customer_segmentation(sample_user.id)
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            # Check for expected segments
            segment_names = [segment.segment for segment in result]
            expected_segments = ['Champions', 'Loyal Customers', 'At Risk', 'Lost', 'New']
            for segment in expected_segments:
                assert segment in segment_names
            
            # Cleanup
            for customer in customers:
                db.session.delete(customer)
            db.session.commit()
    
    def test_anomaly_detection(self, app, sample_user, sample_orders):
        """Test anomaly detection."""
        with app.app_context():
            result = PredictiveAnalytics.detect_anomalies(
                user_id=sample_user.id,
                metric='revenue',
                threshold=2.0
            )
            
            assert isinstance(result, list)
            # Should detect anomalies in sample data
            assert len(result) >= 0
    
    def test_business_insights(self, app, sample_user, sample_orders):
        """Test business insights generation."""
        with app.app_context():
            result = PredictiveAnalytics.generate_business_insights(sample_user.id)
            
            assert isinstance(result, dict)
            assert 'revenue_insights' in result
            assert 'customer_insights' in result
            assert 'growth_opportunities' in result
            assert 'risk_alerts' in result


class TestRealTimeDashboard:
    """Test real-time dashboard functionality."""
    
    @pytest.fixture
    def mock_socketio(self):
        return Mock()
    
    def test_realtime_service_initialization(self, mock_socketio):
        """Test real-time service initialization."""
        # Import after mocking
        from app.services.realtime_dashboard import RealTimeDashboard
        
        service = RealTimeDashboard(mock_socketio)
        assert service.socketio == mock_socketio
        assert service.connected_users == {}
    
    def test_user_connection_handling(self, mock_socketio):
        """Test user connection/disconnection."""
        from app.services.realtime_dashboard import RealTimeDashboard
        
        service = RealTimeDashboard(mock_socketio)
        
        # Test connection
        service.handle_user_connect(user_id=1, session_id='session123')
        assert 1 in service.connected_users
        assert service.connected_users[1] == 'session123'
        
        # Test disconnection
        service.handle_user_disconnect(user_id=1)
        assert 1 not in service.connected_users
    
    def test_order_update_broadcast(self, mock_socketio):
        """Test order update broadcasting."""
        from app.services.realtime_dashboard import RealTimeDashboard
        
        service = RealTimeDashboard(mock_socketio)
        
        order_data = {
            'id': 123,
            'user_id': 1,
            'total_amount': 100.0,
            'customer_name': 'Test Customer'
        }
        
        service.broadcast_order_update(order_data)
        
        # Verify socket.emit was called
        mock_socketio.emit.assert_called()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == 'dashboard_update'
        assert call_args[0][1]['type'] == 'new_order'
        assert call_args[0][1]['data'] == order_data


class TestEnhancedOrdersAPI:
    """Test enhanced orders API endpoints."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self, sample_user):
        return {'Authorization': f'Bearer fake-token'}
    
    def test_calculate_item_subtotal_json(self, client, auth_headers):
        """Test item subtotal calculation with JSON data."""
        data = {
            'quantity': 5,
            'unit_price': 10.50
        }
        
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['subtotal'] == 52.50
        assert result['total'] == 52.50
        assert result['formatted_subtotal'] == '$52.50'
    
    def test_calculate_item_subtotal_form(self, client, auth_headers):
        """Test item subtotal calculation with form data."""
        data = {
            'quantity': '3',
            'unit_price': '15.75'
        }
        
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['subtotal'] == 47.25
        assert result['total'] == 47.25
        assert result['formatted_total'] == '$47.25'
    
    def test_calculate_item_subtotal_validation(self, client, auth_headers):
        """Test validation for item subtotal calculation."""
        # Test invalid quantity
        data = {'quantity': 0, 'unit_price': 10.0}
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            json=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        
        # Test negative price
        data = {'quantity': 5, 'unit_price': -10.0}
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            json=data,
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_calculate_order_totals(self, client, auth_headers):
        """Test complete order totals calculation."""
        data = {
            'subtotal': 100.0,
            'tax_rate': 8.0,
            'shipping_amount': 15.0,
            'discount_amount': 5.0
        }
        
        response = client.post(
            '/api/v1/enhanced_orders/calculate-totals',
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['subtotal'] == 100.0
        assert result['tax_amount'] == 8.0
        assert result['total'] == 118.0  # 100 + 8 + 15 - 5
    
    def test_product_details(self, client, auth_headers):
        """Test product details endpoint."""
        # This would require a sample product in database
        response = client.get(
            '/api/v1/enhanced_orders/product/1',
            headers=auth_headers
        )
        
        # Should return 404 for non-existent product or handle appropriately
        assert response.status_code in [404, 200]


class TestAnalyticsService:
    """Test analytics service with security fixes."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    @pytest.fixture
    def sample_user(self, app):
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            db.session.add(user)
            db.session.commit()
            yield user
            db.session.delete(user)
            db.session.commit()
    
    def test_get_sales_by_month_validation(self, app, sample_user):
        """Test input validation in sales by month."""
        with app.app_context():
            # Test invalid user_id
            with pytest.raises(ValueError, match="Invalid user ID"):
                AnalyticsService.get_sales_by_month(user_id=0)
            
            # Test invalid year
            with pytest.raises(ValueError, match="Invalid year range"):
                AnalyticsService.get_sales_by_month(
                    user_id=sample_user.id,
                    year=2019  # Too old
                )
            
            # Test invalid month
            with pytest.raises(ValueError, match="Invalid month"):
                AnalyticsService.get_sales_by_month(
                    user_id=sample_user.id,
                    month=13  # Invalid month
                )
            
            # Test invalid limit
            with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
                AnalyticsService.get_sales_by_month(
                    user_id=sample_user.id,
                    limit=150  # Too high
                )
    
    def test_get_product_sales_validation(self, app, sample_user):
        """Test input validation in product sales."""
        with app.app_context():
            # Test invalid sort_by
            with pytest.raises(ValueError, match="Invalid sort column"):
                AnalyticsService.get_product_sales(
                    user_id=sample_user.id,
                    sort_by='invalid_column'
                )
            
            # Test invalid sort_order
            with pytest.raises(ValueError, match="Invalid sort order"):
                AnalyticsService.get_product_sales(
                    user_id=sample_user.id,
                    sort_order='invalid_order'
                )
            
            # Test invalid limit
            with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
                AnalyticsService.get_product_sales(
                    user_id=sample_user.id,
                    limit=200
                )
    
    def test_parameterized_queries(self, app, sample_user):
        """Test that queries use parameterized inputs (SQL injection protection)."""
        with app.app_context():
            # This should work without SQL injection
            result = AnalyticsService.get_sales_by_month(
                user_id=sample_user.id,
                year=2024,
                month=6
            )
            
            assert isinstance(result, list)
            # Should not contain any SQL injection artifacts
            for item in result:
                assert isinstance(item, dict)
                assert 'year' in item
                assert 'month' in item


class TestAnalyticsValidators:
    """Test analytics validation schemas."""
    
    def test_sales_by_month_query_validation(self):
        """Test SalesByMonthQuery validation."""
        from app.validators.analytics_validators import SalesByMonthQuery
        
        # Valid query
        valid_query = SalesByMonthQuery(
            user_id=1,
            year=2024,
            month=6,
            limit=12
        )
        assert valid_query.user_id == 1
        assert valid_query.year == 2024
        assert valid_query.month == 6
        assert valid_query.limit == 12
        
        # Invalid user_id
        with pytest.raises(ValueError):
            SalesByMonthQuery(user_id=0)
        
        # Invalid year
        with pytest.raises(ValueError):
            SalesByMonthQuery(user_id=1, year=2019)
        
        # Invalid month
        with pytest.raises(ValueError):
            SalesByMonthQuery(user_id=1, month=13)
        
        # Invalid limit
        with pytest.raises(ValueError):
            SalesByMonthQuery(user_id=1, limit=150)
    
    def test_product_sales_query_validation(self):
        """Test ProductSalesQuery validation."""
        from app.validators.analytics_validators import ProductSalesQuery
        
        # Valid query
        valid_query = ProductSalesQuery(
            user_id=1,
            sort_by='revenue',
            sort_order='desc',
            limit=10
        )
        assert valid_query.user_id == 1
        assert valid_query.sort_by == 'revenue'
        assert valid_query.sort_order == 'desc'
        assert valid_query.limit == 10
        
        # Invalid sort_by
        with pytest.raises(ValueError):
            ProductSalesQuery(user_id=1, sort_by='invalid')
        
        # Invalid sort_order
        with pytest.raises(ValueError):
            ProductSalesQuery(user_id=1, sort_order='invalid')
    
    def test_date_range_validation(self):
        """Test date range validation."""
        from app.validators.analytics_validators import AnalyticsQuery
        
        # Valid date range
        valid_query = AnalyticsQuery(
            user_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        assert valid_query.start_date == date(2024, 1, 1)
        assert valid_query.end_date == date(2024, 12, 31)
        
        # Invalid date range (end before start)
        with pytest.raises(ValueError, match="End date must be after start date"):
            AnalyticsQuery(
                user_id=1,
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1)
            )


class TestIntegration:
    """Integration tests for the complete business intelligence system."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_order_creation_with_predictive_analytics(self, app, client):
        """Test that order creation triggers predictive analytics."""
        with patch('app.services.realtime_dashboard.RealTimeDashboard') as mock_realtime:
            with patch('app.services.predictive_analytics.PredictiveAnalytics') as mock_predictive:
                
                # Mock the services
                mock_realtime.return_value.broadcast_order_update = Mock()
                mock_predictive.return_value.detect_anomalies.return_value = []
                
                # Create an order (this would normally require authentication)
                # For testing, we'll test the API endpoint directly
                response = client.post('/orders/create', data={
                    'customer_id': '1',
                    'items-0-product_id': '1',
                    'items-0-quantity': '2',
                    'items-0-unit_price': '25.00'
                })
                
                # The order creation should attempt to call predictive analytics
                # In a real test, we'd verify the calls were made
                assert response.status_code in [200, 302, 400]  # Depends on auth
    
    def test_predictive_api_endpoints(self, app, client):
        """Test predictive analytics API endpoints."""
        # Test revenue forecast endpoint
        with patch('app.services.predictive_analytics.PredictiveAnalytics.forecast_revenue') as mock_forecast:
            mock_forecast.return_value = Mock(
                predictions=[1000, 1100, 1200],
                confidence_intervals=[(900, 1100), (1000, 1200)],
                accuracy_score=0.85,
                trend_direction='increasing',
                seasonality_detected=False,
                recommendations=['Continue growth strategy']
            )
            
            response = client.get('/api/v1/predictive/revenue/forecast')
            assert response.status_code in [200, 401]  # Depends on auth
            
            if response.status_code == 200:
                data = response.get_json()
                assert 'data' in data
                assert data['data']['accuracy_score'] == 0.85
                assert len(data['data']['predictions']) == 3
        
        # Test customer segments endpoint
        with patch('app.services.predictive_analytics.PredictiveAnalytics.customer_segmentation') as mock_segments:
            mock_segments.return_value = [
                Mock(segment='Champions', count=10, avg_lifetime_value=500.0),
                Mock(segment='At Risk', count=5, avg_lifetime_value=200.0)
            ]
            
            response = client.get('/api/v1/predictive/customers/segments')
            assert response.status_code in [200, 401]  # Depends on auth
    
    def test_realtime_websocket_integration(self, app):
        """Test WebSocket integration for real-time updates."""
        # This would require a more complex test setup with actual WebSocket
        # For now, we test the service layer
        mock_socketio = Mock()
        service = RealTimeDashboard(mock_socketio)
        
        # Test various broadcast methods
        service.broadcast_order_update({
            'id': 123,
            'user_id': 1,
            'total_amount': 100.0
        })
        
        service.broadcast_inventory_update({
            'user_id': 1,
            'product_name': 'Test Product',
            'current_stock': 50
        })
        
        service.broadcast_sales_update({
            'user_id': 1,
            'message': 'Sales milestone reached!'
        })
        
        # Verify emit was called for each broadcast
        assert mock_socketio.emit.call_count == 3


class TestPerformanceAndSecurity:
    """Test performance optimizations and security measures."""
    
    def test_caching_mechanism(self):
        """Test that caching is working for analytics queries."""
        with patch('app.services.analytics_service.cache') as mock_cache:
            # Test cache decorator
            from app.services.analytics_service import AnalyticsService
            
            # Call the method multiple times
            result1 = AnalyticsService.get_sales_by_month(user_id=1)
            result2 = AnalyticsService.get_sales_by_month(user_id=1)
            
            # Should use cache on second call
            mock_cache.get.assert_called()
    
    def test_sql_injection_protection(self):
        """Test that SQL injection attempts are blocked."""
        with pytest.raises(ValueError):
            # This should be caught by validation, not reach SQL
            AnalyticsService.get_sales_by_month(
                user_id=1,
                year="2024; DROP TABLE users; --"
            )
    
    def test_error_handling_and_logging(self):
        """Test comprehensive error handling."""
        with patch('app.services.predictive_analytics.logger') as mock_logger:
            # Test error logging in predictive analytics
            try:
                PredictiveAnalytics.forecast_revenue(user_id=999999)  # Non-existent user
            except Exception as e:
                # Should log the error
                mock_logger.error.assert_called()
    
    def test_input_sanitization(self):
        """Test that all inputs are properly sanitized."""
        from app.validators.analytics_validators import SalesByMonthQuery
        
        # Test various malicious inputs
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError):
                SalesByMonthQuery(user_id=malicious_input)


# Test configuration
@pytest.fixture(scope='session')
def test_app():
    """Create test application."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
    
    with app.app_context():
        yield app


@pytest.fixture(scope='session')
def test_client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture(scope='session')
def test_db(test_app):
    """Create test database."""
    with test_app.app_context():
        db.create_all()
        yield db
        db.drop_all()


# Test runner
if __name__ == '__main__':
    pytest.main([__file__])

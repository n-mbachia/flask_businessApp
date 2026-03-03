"""
Tests for enhanced orders API functionality.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
import json

from app import create_app, db
from app.models import User, Product, Order
from app.api.v1.enhanced_orders import CalculateItemSubtotal, CalculateOrderTotals


class TestEnhancedOrdersAPI:
    """Test enhanced orders API endpoints."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
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
    def sample_product(self, app, sample_user):
        with app.app_context():
            product = Product(
                user_id=sample_user.id,
                name='Test Product',
                price=Decimal('25.00'),
                current_stock=100,
                track_inventory=True
            )
            db.session.add(product)
            db.session.commit()
            yield product
            db.session.delete(product)
            db.session.commit()
    
    def test_calculate_item_subtotal_json_success(self, client, sample_user):
        """Test successful item subtotal calculation with JSON data."""
        # Mock authentication
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': 5,
                'unit_price': 10.50
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['subtotal'] == 52.50
            assert result['total'] == 52.50
            assert result['formatted_subtotal'] == '$52.50'
            assert result['formatted_total'] == '$52.50'
    
    def test_calculate_item_subtotal_form_success(self, client, sample_user):
        """Test successful item subtotal calculation with form data."""
        # Mock authentication
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': '3',
                'unit_price': '15.75'
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['subtotal'] == 47.25
            assert result['total'] == 47.25
            assert result['formatted_total'] == '$47.25'
    
    def test_calculate_item_subtotal_decimal_precision(self, client, sample_user):
        """Test decimal precision in calculations."""
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': '3',
                'unit_price': '0.333333333333'
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                data=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            # Should be properly rounded to 2 decimal places
            assert result['subtotal'] == 1.0  # 3 * 0.333333333333 = 1.0
            assert result['total'] == 1.0
    
    def test_calculate_item_subtotal_invalid_quantity(self, client, sample_user):
        """Test validation with invalid quantity."""
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': 0,  # Invalid: must be > 0
                'unit_price': 10.0
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 400
            error_response = response.get_json()
            assert 'Quantity must be greater than 0' in str(error_response)
    
    def test_calculate_item_subtotal_negative_price(self, client, sample_user):
        """Test validation with negative price."""
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': 5,
                'unit_price': -10.0  # Invalid: must be >= 0
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 400
            error_response = response.get_json()
            assert 'Unit price cannot be negative' in str(error_response)
    
    def test_calculate_item_subtotal_missing_data(self, client, sample_user):
        """Test handling of missing required data."""
        with patch('flask_login.current_user', sample_user):
            data = {
                'quantity': 5
                # Missing unit_price
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 400
    
    def test_calculate_order_totals_success(self, client, sample_user):
        """Test successful order totals calculation."""
        with patch('flask_login.current_user', sample_user):
            data = {
                'subtotal': 100.0,
                'tax_rate': 8.0,
                'shipping_amount': 15.0,
                'discount_amount': 5.0
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-totals',
                json=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['subtotal'] == 100.0
            assert result['tax_amount'] == 8.0  # 100 * 0.08
            assert result['total'] == 118.0  # 100 + 8 + 15 - 5
            assert result['formatted_total'] == '$118.00'
    
    def test_calculate_order_totals_validation(self, client, sample_user):
        """Test validation in order totals calculation."""
        with patch('flask_login.current_user', sample_user):
            # Test negative subtotal
            data = {
                'subtotal': -100.0,
                'tax_rate': 8.0,
                'shipping_amount': 15.0,
                'discount_amount': 5.0
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-totals',
                json=data
            )
            
            assert response.status_code == 400
            error_response = response.get_json()
            assert 'Subtotal cannot be negative' in str(error_response)
    
    def test_product_details_success(self, client, sample_user, sample_product):
        """Test successful product details retrieval."""
        with patch('flask_login.current_user', sample_user):
            response = client.get(
                f'/api/v1/enhanced_orders/product/{sample_product.id}'
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['id'] == sample_product.id
            assert result['name'] == 'Test Product'
            assert result['price'] == 25.0
            assert result['stock_quantity'] == 100
            assert result['track_inventory'] == True
    
    def test_product_details_not_found(self, client, sample_user):
        """Test product details for non-existent product."""
        with patch('flask_login.current_user', sample_user):
            response = client.get(
                '/api/v1/enhanced_orders/product/99999'
            )
            
            assert response.status_code == 404
    
    def test_product_details_unauthorized(self, client):
        """Test product details without authentication."""
        response = client.get(
            '/api/v1/enhanced_orders/product/1'
        )
        
        # Should require authentication
        assert response.status_code in [401, 403]
    
    def test_status_change_warnings(self, client, sample_user):
        """Test status change warning generation."""
        with patch('flask_login.current_user', sample_user):
            # Test completed status
            data = {'status': 'completed'}
            response = client.post(
                '/api/v1/enhanced_orders/status-change',
                json=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['has_warnings'] == True
            assert len(result['warnings']) == 2
            assert any('inventory will be updated' in warning for warning in result['warnings'])
            assert any('customer will be notified' in warning for warning in result['warnings'])
            
            # Test cancelled status
            data = {'status': 'cancelled'}
            response = client.post(
                '/api/v1/enhanced_orders/status-change',
                json=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert 'items will be returned to inventory' in str(result)
    
    def test_error_handling_and_logging(self, client, sample_user):
        """Test error handling and logging."""
        with patch('app.api.v1.enhanced_orders.logger') as mock_logger:
            # Test with malformed data that causes exception
            data = {
                'quantity': 'invalid_number',
                'unit_price': 10.0
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 400
            # Should log the error
            mock_logger.error.assert_called()
    
    def test_content_type_handling(self, client, sample_user):
        """Test handling of different content types."""
        with patch('flask_login.current_user', sample_user):
            # Test JSON content type
            json_data = {'quantity': 2, 'unit_price': 15.0}
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=json_data,
                headers={'Content-Type': 'application/json'}
            )
            assert response.status_code == 200
            
            # Test form content type
            form_data = {'quantity': '2', 'unit_price': '15.0'}
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                data=form_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            assert response.status_code == 200
    
    def test_htmx_integration(self, client, sample_user):
        """Test HTMX-specific integration."""
        with patch('flask_login.current_user', sample_user):
            # Simulate HTMX request with custom headers
            data = {'quantity': '3', 'unit_price': '25.50'}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'  # HTMX header
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                data=data,
                headers=headers
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['subtotal'] == 76.5  # 3 * 25.50
    
    def test_edge_cases(self, client, sample_user):
        """Test edge cases and boundary conditions."""
        with patch('flask_login.current_user', sample_user):
            # Test very large numbers
            data = {
                'quantity': 999999,
                'unit_price': 99999.99
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            # Should handle large numbers correctly
            assert result['subtotal'] == 999999 * 99999.99
            
            # Test very small numbers
            data = {
                'quantity': 1,
                'unit_price': 0.01
            }
            
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['subtotal'] == 0.01
    
    def test_concurrent_requests(self, client, sample_user):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            data = {'quantity': 2, 'unit_price': 10.0}
            response = client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
            results.append(response.status_code)
        
        # Create multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestEnhancedOrdersIntegration:
    """Integration tests for enhanced orders with other components."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_order_form_integration(self, client):
        """Test integration with order form."""
        # This would test the actual form integration
        # For now, test the API endpoints that the form calls
        
        # Test the sequence of calls the form would make
        # 1. Get product details
        response = client.get('/api/v1/enhanced_orders/product/1')
        
        # 2. Calculate subtotal
        data = {'quantity': 2, 'unit_price': 25.0}
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            json=data
        )
        
        assert response.status_code == 200
        
        # 3. Calculate order totals
        totals_data = {
            'subtotal': 50.0,
            'tax_rate': 8.0,
            'shipping_amount': 10.0,
            'discount_amount': 5.0
        }
        response = client.post(
            '/api/v1/enhanced_orders/calculate-totals',
            json=totals_data
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['total'] == 55.0  # 50 + 4 + 10 - 5
    
    def test_error_recovery(self, client):
        """Test error recovery and graceful degradation."""
        with patch('app.api.v1.enhanced_orders.logger') as mock_logger:
            # Simulate various error conditions
            test_cases = [
                {'quantity': 'invalid', 'unit_price': 10.0},
                {'quantity': 0, 'unit_price': 10.0},
                {'quantity': 5, 'unit_price': -10.0},
                {'quantity': None, 'unit_price': 10.0},
                {'quantity': 5, 'unit_price': None}
            ]
            
            for data in test_cases:
                response = client.post(
                    '/api/v1/enhanced_orders/calculate-item-subtotal',
                    json=data
                )
                
                # Should handle all errors gracefully
                assert response.status_code == 400
                error_response = response.get_json()
                assert 'error' in str(error_response) or 'Calculation failed' in str(error_response)


# Performance tests
class TestEnhancedOrdersPerformance:
    """Performance tests for enhanced orders API."""
    
    @pytest.fixture
    def app(self):
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_response_time(self, client):
        """Test API response times."""
        import time
        
        data = {'quantity': 5, 'unit_price': 10.0}
        
        start_time = time.time()
        response = client.post(
            '/api/v1/enhanced_orders/calculate-item-subtotal',
            json=data
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should respond quickly (under 100ms)
        assert response_time < 0.1
    
    def test_memory_usage(self, client):
        """Test memory efficiency of calculations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for i in range(100):
            data = {'quantity': i + 1, 'unit_price': 10.0}
            client.post(
                '/api/v1/enhanced_orders/calculate-item-subtotal',
                json=data
            )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB


if __name__ == '__main__':
    pytest.main([__file__])

"""
Unit tests for OrderService.
Tests all order service functionality with various scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.services.order_service import OrderService
from app.models import Order, OrderItem, Customer, Product
from app.utils.exceptions import ValidationError, BusinessLogicError, NotFoundError


class TestOrderService:
    """Test suite for OrderService."""
    
    @pytest.fixture
    def mock_user_id(self):
        """Mock user ID for testing."""
        return 1
    
    @pytest.fixture
    def valid_order_data(self):
        """Valid order data for testing."""
        return {
            'customer_id': 1,
            'status': Order.STATUS_PENDING,
            'payment_status': Order.PAYMENT_UNPAID,
            'is_recurring': False,
            'notes': 'Test order notes'
        }
    
    @pytest.fixture
    def valid_items_data(self):
        """Valid items data for testing."""
        return [
            {
                'product_id': 1,
                'quantity': 2,
                'unit_price': 10.50,
                'notes': 'Test item 1'
            },
            {
                'product_id': 2,
                'quantity': 1,
                'unit_price': 25.00,
                'notes': 'Test item 2'
            }
        ]
    
    @pytest.fixture
    def mock_order(self):
        """Mock order object."""
        order = Mock(spec=Order)
        order.id = 1
        order.customer_id = 1
        order.user_id = 1
        order.status = Order.STATUS_PENDING
        order.payment_status = Order.PAYMENT_UNPAID
        order.total_amount = Decimal('46.00')
        order.is_recurring = False
        order.notes = 'Test order notes'
        order.created_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        return order
    
    @pytest.fixture
    def mock_customer(self):
        """Mock customer object."""
        customer = Mock(spec=Customer)
        customer.id = 1
        customer.name = 'John Doe'
        customer.email = 'john.doe@example.com'
        customer.is_active = True
        return customer
    
    @pytest.fixture
    def mock_product(self):
        """Mock product object."""
        product = Mock(spec=Product)
        product.id = 1
        product.name = 'Test Product'
        product.selling_price_per_unit = Decimal('10.50')
        product.quantity_available = 100
        product.is_active = True
        return product
    
    def test_create_order_success(self, valid_order_data, valid_items_data, mock_user_id, mock_order, mock_customer):
        """Test successful order creation."""
        with patch('app.services.order_service.db.session') as mock_session, \
             patch('app.services.order_service.Order') as mock_order_class, \
             patch.object(OrderService, '_validate_order_data') as mock_validate, \
             patch.object(OrderService, '_get_and_validate_customer') as mock_get_customer, \
             patch.object(OrderService, '_validate_and_prepare_items') as mock_validate_items, \
             patch.object(OrderService, '_create_order_entity') as mock_create_entity, \
             patch.object(OrderService, '_update_inventory_for_order') as mock_update_inventory:
            
            # Setup mocks
            mock_validate.return_value = None
            mock_get_customer.return_value = mock_customer
            mock_validate_items.return_value = valid_items_data
            mock_create_entity.return_value = mock_order
            mock_session.add.return_value = None
            mock_session.flush.return_value = None
            mock_session.commit.return_value = None
            
            # Execute
            result = OrderService.create_order(mock_user_id, valid_order_data, valid_items_data)
            
            # Assertions
            assert result == mock_order
            mock_validate.assert_called_once_with(valid_order_data, valid_items_data)
            mock_get_customer.assert_called_once_with(1, mock_user_id)
            mock_validate_items.assert_called_once_with(valid_items_data, mock_user_id, False)
            mock_create_entity.assert_called_once_with(mock_user_id, valid_order_data, mock_customer, valid_items_data)
            mock_session.add.assert_called_once_with(mock_order)
            mock_session.commit.assert_called_once()
    
    def test_create_order_validation_error(self, valid_order_data, valid_items_data, mock_user_id):
        """Test order creation with validation error."""
        with patch('app.services.order_service.db.session') as mock_session, \
             patch.object(OrderService, '_validate_order_data') as mock_validate:
            
            mock_validate.side_effect = ValidationError('Invalid order data')
            mock_session.rollback.return_value = None
            
            with pytest.raises(ValidationError) as exc_info:
                OrderService.create_order(mock_user_id, valid_order_data, valid_items_data)
            
            assert 'Invalid order data' in str(exc_info.value)
            mock_session.rollback.assert_called_once()
    
    def test_create_order_customer_not_found(self, valid_order_data, valid_items_data, mock_user_id):
        """Test order creation with customer not found."""
        with patch('app.services.order_service.db.session') as mock_session, \
             patch.object(OrderService, '_validate_order_data') as mock_validate, \
             patch.object(OrderService, '_get_and_validate_customer') as mock_get_customer:
            
            mock_validate.return_value = None
            mock_get_customer.side_effect = NotFoundError('Customer not found')
            mock_session.rollback.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                OrderService.create_order(mock_user_id, valid_order_data, valid_items_data)
            
            assert 'Customer not found' in str(exc_info.value)
            mock_session.rollback.assert_called_once()
    
    def test_update_order_success(self, valid_order_data, valid_items_data, mock_user_id, mock_order):
        """Test successful order update."""
        update_data = {'status': Order.STATUS_PROCESSING, 'notes': 'Updated notes'}
        
        with patch('app.services.order_service.db.session') as mock_session, \
             patch.object(OrderService, '_get_order_for_user') as mock_get_order, \
             patch.object(OrderService, '_validate_order_update_allowed') as mock_validate_update, \
             patch.object(OrderService, '_update_order_fields') as mock_update_fields, \
             patch.object(OrderService, '_update_order_items') as mock_update_items:
            
            # Setup mocks
            mock_get_order.return_value = mock_order
            mock_validate_update.return_value = None
            mock_update_fields.return_value = None
            mock_update_items.return_value = None
            mock_session.commit.return_value = None
            
            # Execute
            result = OrderService.update_order(1, mock_user_id, update_data, valid_items_data)
            
            # Assertions
            assert result == mock_order
            mock_get_order.assert_called_once_with(1, mock_user_id)
            mock_validate_update.assert_called_once_with(mock_order)
            mock_update_fields.assert_called_once_with(mock_order, update_data)
            mock_update_items.assert_called_once_with(mock_order, valid_items_data, mock_user_id)
            mock_session.commit.assert_called_once()
    
    def test_complete_order_success(self, mock_user_id, mock_order):
        """Test successful order completion."""
        mock_order.status = Order.STATUS_PENDING
        
        with patch.object(OrderService, '_get_order_for_user') as mock_get_order:
            mock_get_order.return_value = mock_order
            def _mark_complete(session):
                mock_order.status = Order.STATUS_COMPLETED
                return True
            mock_order.mark_as_completed.return_value = True
            mock_order.mark_as_completed.side_effect = _mark_complete

            result = OrderService.complete_order(1, mock_user_id)

            assert result == mock_order
            assert result.status == Order.STATUS_COMPLETED
            mock_get_order.assert_called_once_with(1, mock_user_id)
    
    def test_complete_order_already_completed(self, mock_user_id, mock_order):
        """Test completing an already completed order."""
        mock_order.status = Order.STATUS_COMPLETED
        
        with patch.object(OrderService, '_get_order_for_user') as mock_get_order:
            mock_get_order.return_value = mock_order
            
            result = OrderService.complete_order(1, mock_user_id)
            
            assert result == mock_order
            assert result.status == Order.STATUS_COMPLETED
    
    def test_complete_order_cancelled_order(self, mock_user_id, mock_order):
        """Test completing a cancelled order."""
        mock_order.status = Order.STATUS_CANCELLED
        
        with patch.object(OrderService, '_get_order_for_user') as mock_get_order:
            mock_get_order.return_value = mock_order
            
            with pytest.raises(BusinessLogicError) as exc_info:
                OrderService.complete_order(1, mock_user_id)
            
            assert 'Cannot complete a cancelled order' in str(exc_info.value)
    
    def test_cancel_order_success(self, mock_user_id, mock_order):
        """Test successful order cancellation."""
        mock_order.status = Order.STATUS_PENDING
        
        with patch('app.services.order_service.db.session') as mock_session, \
             patch.object(OrderService, '_get_order_for_user') as mock_get_order, \
             patch.object(OrderService, '_return_inventory_for_order') as mock_return_inventory:
            
            # Setup mocks
            mock_get_order.return_value = mock_order
            mock_return_inventory.return_value = None
            mock_session.commit.return_value = None
            
            result = OrderService.cancel_order(1, mock_user_id)
            
            assert result == mock_order
            assert result.status == Order.STATUS_CANCELLED
            mock_get_order.assert_called_once_with(1, mock_user_id)
            mock_session.commit.assert_called_once()
    
    def test_get_orders_for_user_success(self, mock_user_id):
        """Test successful order retrieval for user."""
        filters = {'status': Order.STATUS_PENDING}
        orders = [Mock(spec=Order) for _ in range(5)]
        
        with patch('app.services.order_service.Order') as mock_order_class:
            mock_query = Mock()
            mock_order_class.query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            
            # Mock pagination
            mock_pagination = Mock()
            mock_pagination.items = orders
            mock_pagination.total = 5
            mock_query.paginate.return_value = mock_pagination
            
            result_orders, total = OrderService.get_orders_for_user(mock_user_id, filters)
            
            assert result_orders == orders
            assert total == 5
            mock_query.paginate.assert_called_once_with(page=1, per_page=20, error_out=False)
    
    def test_calculate_order_totals_success(self, valid_items_data):
        """Test successful order totals calculation."""
        tax_rate = Decimal('0.16')  # 16%
        shipping_amount = Decimal('5.00')
        discount_amount = Decimal('2.00')
        
        result = OrderService.calculate_order_totals(
            valid_items_data, tax_rate, shipping_amount, discount_amount
        )
        
        # Expected calculations:
        # Subtotal: (2 * 10.50) + (1 * 25.00) = 46.00
        # Tax: 46.00 * 0.16 = 7.36
        # Total: 46.00 + 7.36 + 5.00 - 2.00 = 56.36
        
        assert result['subtotal'] == Decimal('46.00')
        assert result['tax_amount'] == Decimal('7.36')
        assert result['shipping_amount'] == Decimal('5.00')
        assert result['discount_amount'] == Decimal('2.00')
        assert result['total'] == Decimal('56.36')
    
    def test_calculate_order_totals_empty_items(self):
        """Test order totals calculation with empty items."""
        result = OrderService.calculate_order_totals([])
        
        assert result['subtotal'] == Decimal('0')
        assert result['tax_amount'] == Decimal('0')
        assert result['total'] == Decimal('0')
    
    def test_calculate_order_totals_negative_total(self):
        """Test order totals calculation with negative total."""
        items_data = [{'product_id': 1, 'quantity': 1, 'unit_price': 10.00}]
        discount_amount = Decimal('50.00')  # Large discount
        
        result = OrderService.calculate_order_totals(
            items_data, Decimal('0'), Decimal('0'), discount_amount
        )
        
        # Total should not be negative
        assert result['total'] == Decimal('0')
    
    # Test private helper methods
    
    def test_validate_order_data_valid(self, valid_order_data, valid_items_data):
        """Test validation of valid order data."""
        # Should not raise any exception
        OrderService._validate_order_data(valid_order_data, valid_items_data)
    
    def test_validate_order_data_no_items(self, valid_order_data):
        """Test validation with no items."""
        with pytest.raises(ValidationError) as exc_info:
            OrderService._validate_order_data(valid_order_data, [])
        
        assert 'At least one order item is required' in str(exc_info.value)
    
    def test_validate_order_data_no_valid_items(self, valid_order_data):
        """Test validation with no valid items."""
        invalid_items = [{'product_id': None, 'quantity': 0}]
        
        with pytest.raises(ValidationError) as exc_info:
            OrderService._validate_order_data(valid_order_data, invalid_items)
        
        assert 'At least one valid order item is required' in str(exc_info.value)
    
    def test_get_and_validate_customer_success(self, mock_user_id, mock_customer):
        """Test successful customer validation."""
        with patch('app.services.order_service.Customer') as mock_customer_class:
            mock_customer_class.query.filter_by.return_value.first.return_value = mock_customer
            
            result = OrderService._get_and_validate_customer(1, mock_user_id)
            
            assert result == mock_customer
            mock_customer_class.query.filter_by.assert_called_once_with(id=1, user_id=mock_user_id)
    
    def test_get_and_validate_customer_not_found(self, mock_user_id):
        """Test customer validation with not found."""
        with patch('app.services.order_service.Customer') as mock_customer_class:
            mock_customer_class.query.filter_by.return_value.first.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                OrderService._get_and_validate_customer(999, mock_user_id)
            
            assert 'Customer with ID 999 not found' in str(exc_info.value)
    
    def test_get_and_validate_customer_inactive(self, mock_user_id, mock_customer):
        """Test customer validation with inactive customer."""
        mock_customer.is_active = False
        
        with patch('app.services.order_service.Customer') as mock_customer_class:
            mock_customer_class.query.filter_by.return_value.first.return_value = mock_customer
            
            with pytest.raises(ValidationError) as exc_info:
                OrderService._get_and_validate_customer(1, mock_user_id)
            
            assert 'Selected customer is not active' in str(exc_info.value)
    
    def test_validate_and_prepare_items_success(self, valid_items_data, mock_user_id, mock_product):
        """Test successful items validation and preparation."""
        with patch('app.services.order_service.Product') as mock_product_class, \
             patch('app.services.order_service.InventoryService') as mock_inventory_service:
            
            # Setup mocks
            mock_product_class.query.filter_by.return_value.first.return_value = mock_product
            mock_inventory_service.validate_order_items.return_value = (True, [])
            
            result = OrderService._validate_and_prepare_items(valid_items_data, mock_user_id)
            
            assert len(result) == 2
            assert result[0]['product_id'] == 1
            assert result[0]['quantity'] == 2.0
            assert result[0]['unit_price'] == Decimal('10.50')
    
    def test_validate_and_prepare_items_product_not_found(self, valid_items_data, mock_user_id):
        """Test items validation with product not found."""
        with patch('app.services.order_service.Product') as mock_product_class:
            mock_product_class.query.filter_by.return_value.first.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                OrderService._validate_and_prepare_items(valid_items_data, mock_user_id)
            
            assert 'Product with ID 1 not found' in str(exc_info.value)
    
    def test_validate_and_prepare_items_insufficient_inventory(self, valid_items_data, mock_user_id, mock_product):
        """Test items validation with insufficient inventory."""
        with patch('app.services.order_service.Product') as mock_product_class, \
             patch('app.services.order_service.InventoryService') as mock_inventory_service:
            
            # Setup mocks
            mock_product_class.query.filter_by.return_value.first.return_value = mock_product
            mock_inventory_service.validate_order_items.return_value = (False, [{'success': False, 'message': 'Insufficient stock'}])
            
            with pytest.raises(ValidationError) as exc_info:
                OrderService._validate_and_prepare_items(valid_items_data, mock_user_id)
            
            assert 'Insufficient inventory' in str(exc_info.value)
    
    def test_get_order_for_user_success(self, mock_user_id, mock_order):
        """Test successful order retrieval for user."""
        with patch('app.services.order_service.Order') as mock_order_class:
            mock_order_class.query.filter_by.return_value.first.return_value = mock_order
            
            result = OrderService._get_order_for_user(1, mock_user_id)
            
            assert result == mock_order
            mock_order_class.query.filter_by.assert_called_once_with(id=1, user_id=mock_user_id)
    
    def test_get_order_for_user_not_found(self, mock_user_id):
        """Test order retrieval with not found."""
        with patch('app.services.order_service.Order') as mock_order_class:
            mock_order_class.query.filter_by.return_value.first.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                OrderService._get_order_for_user(999, mock_user_id)
            
            assert 'Order with ID 999 not found' in str(exc_info.value)
    
    def test_validate_order_update_allowed_pending(self, mock_order):
        """Test order update validation for pending order."""
        mock_order.status = Order.STATUS_PENDING
        
        # Should not raise any exception
        OrderService._validate_order_update_allowed(mock_order)
    
    def test_validate_order_update_allowed_completed(self, mock_order):
        """Test order update validation for completed order."""
        mock_order.status = Order.STATUS_COMPLETED
        
        with pytest.raises(BusinessLogicError) as exc_info:
            OrderService._validate_order_update_allowed(mock_order)
        
        assert 'Cannot update a completed order' in str(exc_info.value)
    
    def test_validate_order_update_allowed_cancelled(self, mock_order):
        """Test order update validation for cancelled order."""
        mock_order.status = Order.STATUS_CANCELLED
        
        with pytest.raises(BusinessLogicError) as exc_info:
            OrderService._validate_order_update_allowed(mock_order)
        
        assert 'Cannot update a cancelled order' in str(exc_info.value)
    
    def test_apply_order_filters(self):
        """Test applying filters to order query."""
        mock_query = Mock()
        filters = {
            'status': Order.STATUS_PENDING,
            'customer_id': 1,
            'date_from': '2023-01-01',
            'date_to': '2023-12-31',
            'search_query': 'test'
        }
        # Ensure filter chaining returns the same mock object
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query

        result = OrderService._apply_order_filters(mock_query, filters)

        assert result == mock_query
        assert mock_query.filter.called

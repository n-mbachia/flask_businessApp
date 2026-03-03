"""
Unit tests for CustomerService.
Tests all customer service functionality with various scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.services.customer_service import CustomerService
from app.models import Customer, Order
from app.utils.exceptions import ValidationError, BusinessLogicError, NotFoundError


class TestCustomerService:
    """Test suite for CustomerService."""
    
    @pytest.fixture
    def mock_user_id(self):
        """Mock user ID for testing."""
        return 1
    
    @pytest.fixture
    def valid_customer_data(self):
        """Valid customer data for testing."""
        return {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '+1 (555) 123-4567',
            'company': 'Test Company',
            'address': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'United States',
            'tax_id': '123456789',
            'notes': 'Test customer notes'
        }
    
    @pytest.fixture
    def mock_customer(self):
        """Mock customer object."""
        customer = Mock(spec=Customer)
        customer.id = 1
        customer.name = 'John Doe'
        customer.email = 'john.doe@example.com'
        customer.phone = '+1 (555) 123-4567'
        customer.company = 'Test Company'
        customer.is_active = True
        customer.created_at = datetime.utcnow()
        customer.updated_at = datetime.utcnow()
        return customer
    
    def test_create_customer_success(self, valid_customer_data, mock_user_id, mock_customer):
        """Test successful customer creation."""
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch('app.services.customer_service.Customer') as mock_customer_class, \
             patch.object(CustomerService, '_validate_customer_data') as mock_validate, \
             patch.object(CustomerService, '_check_for_duplicates') as mock_check_duplicates, \
             patch.object(CustomerService, '_create_customer_entity') as mock_create_entity:
            
            # Setup mocks
            mock_validate.return_value = None
            mock_check_duplicates.return_value = None
            mock_create_entity.return_value = mock_customer
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            
            # Execute
            result = CustomerService.create_customer(mock_user_id, valid_customer_data)
            
            # Assertions
            assert result == mock_customer
            mock_validate.assert_called_once_with(valid_customer_data, is_update=False)
            mock_check_duplicates.assert_called_once_with(valid_customer_data, mock_user_id)
            mock_create_entity.assert_called_once_with(mock_user_id, valid_customer_data)
            mock_session.add.assert_called_once_with(mock_customer)
            mock_session.commit.assert_called_once()
    
    def test_create_customer_validation_error(self, valid_customer_data, mock_user_id):
        """Test customer creation with validation error."""
        with patch.object(CustomerService, '_validate_customer_data') as mock_validate:
            mock_validate.side_effect = ValidationError('Invalid name')
            
            with pytest.raises(ValidationError) as exc_info:
                CustomerService.create_customer(mock_user_id, valid_customer_data)
            
            assert 'Invalid name' in str(exc_info.value)
    
    def test_create_customer_duplicate_error(self, valid_customer_data, mock_user_id):
        """Test customer creation with duplicate error."""
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch.object(CustomerService, '_validate_customer_data') as mock_validate, \
             patch.object(CustomerService, '_check_for_duplicates') as mock_check_duplicates:
            
            mock_validate.return_value = None
            mock_check_duplicates.side_effect = BusinessLogicError('Email already exists')
            mock_session.rollback.return_value = None
            
            with pytest.raises(BusinessLogicError) as exc_info:
                CustomerService.create_customer(mock_user_id, valid_customer_data)
            
            assert 'Email already exists' in str(exc_info.value)
            mock_session.rollback.assert_called_once()
    
    def test_update_customer_success(self, valid_customer_data, mock_user_id, mock_customer):
        """Test successful customer update."""
        update_data = {'name': 'Jane Doe', 'email': 'jane.doe@example.com'}
        
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer, \
             patch.object(CustomerService, '_validate_customer_data') as mock_validate, \
             patch.object(CustomerService, '_check_for_duplicates') as mock_check_duplicates, \
             patch.object(CustomerService, '_update_customer_fields') as mock_update_fields:
            
            # Setup mocks
            mock_get_customer.return_value = mock_customer
            mock_validate.return_value = None
            mock_check_duplicates.return_value = None
            mock_update_fields.return_value = None
            mock_session.commit.return_value = None
            
            # Execute
            result = CustomerService.update_customer(1, mock_user_id, update_data)
            
            # Assertions
            assert result == mock_customer
            mock_get_customer.assert_called_once_with(1, mock_user_id)
            mock_validate.assert_called_once_with(update_data, is_update=True)
            mock_check_duplicates.assert_called_once_with(update_data, mock_user_id, exclude_id=1)
            mock_update_fields.assert_called_once_with(mock_customer, update_data)
            mock_session.commit.assert_called_once()
    
    def test_update_customer_not_found(self, valid_customer_data, mock_user_id):
        """Test customer update with not found error."""
        with patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer:
            mock_get_customer.side_effect = NotFoundError('Customer not found')
            
            with pytest.raises(NotFoundError) as exc_info:
                CustomerService.update_customer(999, mock_user_id, valid_customer_data)
            
            assert 'Customer not found' in str(exc_info.value)
    
    def test_get_customer_success(self, mock_user_id, mock_customer):
        """Test successful customer retrieval."""
        with patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            result = CustomerService.get_customer(1, mock_user_id)
            
            assert result == mock_customer
            mock_get_customer.assert_called_once_with(1, mock_user_id)
    
    def test_delete_customer_success(self, mock_user_id, mock_customer):
        """Test successful customer deletion."""
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer, \
             patch('app.services.customer_service.Order') as mock_order_class:
            
            # Setup mocks
            mock_get_customer.return_value = mock_customer
            mock_order_class.query.filter_by.return_value.count.return_value = 0
            mock_session.delete.return_value = None
            mock_session.commit.return_value = None
            
            # Execute
            result = CustomerService.delete_customer(1, mock_user_id)
            
            # Assertions
            assert result is True
            mock_get_customer.assert_called_once_with(1, mock_user_id)
            mock_session.delete.assert_called_once_with(mock_customer)
            mock_session.commit.assert_called_once()
    
    def test_delete_customer_with_orders(self, mock_user_id, mock_customer):
        """Test customer deletion with existing orders."""
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer, \
             patch('app.services.customer_service.Order') as mock_order_class:
            
            # Setup mocks
            mock_get_customer.return_value = mock_customer
            mock_order_class.query.filter_by.return_value.count.return_value = 5
            mock_session.rollback.return_value = None
            
            # Execute
            with pytest.raises(BusinessLogicError) as exc_info:
                CustomerService.delete_customer(1, mock_user_id)
            
            # Assertions
            assert 'Cannot delete customer with 5 existing orders' in str(exc_info.value)
            mock_session.rollback.assert_called_once()
    
    def test_toggle_customer_status_success(self, mock_user_id, mock_customer):
        """Test successful customer status toggle."""
        mock_customer.is_active = True
        
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer:
            
            # Setup mocks
            mock_get_customer.return_value = mock_customer
            mock_session.commit.return_value = None
            
            # Execute
            result = CustomerService.toggle_customer_status(1, mock_user_id)
            
            # Assertions
            assert result == mock_customer
            assert result.is_active is False  # Should be toggled
            mock_get_customer.assert_called_once_with(1, mock_user_id)
            mock_session.commit.assert_called_once()
    
    def test_search_customers_success(self, mock_user_id):
        """Test successful customer search."""
        query = 'John'
        customers = [Mock(spec=Customer) for _ in range(3)]
        
        with patch('app.services.customer_service.Customer') as mock_customer_class:
            mock_query = Mock()
            mock_customer_class.query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value.all.return_value = customers
            
            result = CustomerService.search_customers(mock_user_id, query)
            
            assert result == customers
            mock_query.limit.assert_called_once_with(20)
    
    def test_get_recent_customers_success(self, mock_user_id):
        """Test successful recent customers retrieval."""
        with patch('app.services.customer_service.db.session') as mock_session, \
             patch('app.services.customer_service.Order') as mock_order_class, \
             patch('app.services.customer_service.Customer') as mock_customer_class:

            # Setup mocks
            mock_query = mock_session.query.return_value
            now = datetime.utcnow()
            mock_query.filter_by.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
                (1, now),
                (2, now)
            ]

            mock_customer1 = Mock(spec=Customer)
            mock_customer2 = Mock(spec=Customer)
            mock_customer_class.query.filter.return_value.all.return_value = [mock_customer1, mock_customer2]
            
            result = CustomerService.get_recent_customers(mock_user_id, limit=5)
            
            assert len(result) == 2
            assert mock_customer1 in result
            assert mock_customer2 in result
    
    def test_get_customer_statistics_success(self, mock_user_id, mock_customer):
        """Test successful customer statistics retrieval."""
        with patch.object(CustomerService, '_get_customer_for_user') as mock_get_customer, \
             patch('app.services.customer_service.Order') as mock_order_class, \
             patch('app.services.customer_service.db.session') as mock_session, \
             patch('app.services.customer_service.func') as mock_func:
            
            # Setup mocks
            mock_get_customer.return_value = mock_customer
            
            # Mock order queries
            mock_orders_query = Mock()
            mock_order_class.query.filter_by.return_value = mock_orders_query
            mock_orders_query.count.return_value = 10
            mock_orders_query.filter.return_value.count.return_value = 8
            
            # Mock sum query
            mock_sum_query = Mock()
            mock_session.query.return_value.filter_by.return_value.scalar.return_value = Decimal('1000.50')
            
            # Mock latest order
            mock_latest_order = Mock()
            mock_latest_order.created_at = datetime.utcnow()
            mock_orders_query.order_by.return_value.first.return_value = mock_latest_order
            
            result = CustomerService.get_customer_statistics(1, mock_user_id)
            
            assert result['customer'] == mock_customer
            assert result['total_orders'] == 10
            assert result['completed_orders'] == 8
            assert result['total_spent'] == 1000.5
            assert 'average_order_value' in result
            assert 'last_order_date' in result
    
    def test_import_customers_success(self, mock_user_id, valid_customer_data):
        """Test successful customer import."""
        customers_data = [valid_customer_data, valid_customer_data]
        
        with patch.object(CustomerService, 'create_customer') as mock_create:
            # Setup mocks - first succeeds, second fails
            mock_create.side_effect = [
                Mock(id=1, name='Customer 1'),
                ValidationError('Duplicate email')
            ]
            
            result = CustomerService.import_customers(mock_user_id, customers_data)
            
            assert result['success_count'] == 1
            assert result['error_count'] == 1
            assert len(result['errors']) == 1
            assert len(result['imported_customers']) == 1
    
    # Test private helper methods
    
    def test_validate_customer_data_valid(self, valid_customer_data):
        """Test validation of valid customer data."""
        # Should not raise any exception
        CustomerService._validate_customer_data(valid_customer_data)
    
    def test_validate_customer_data_invalid_name(self, valid_customer_data):
        """Test validation with invalid name."""
        invalid_data = valid_customer_data.copy()
        invalid_data['name'] = 'A'  # Too short
        
        with pytest.raises(ValidationError) as exc_info:
            CustomerService._validate_customer_data(invalid_data)
        
        assert 'Name must be at least 2 characters long' in str(exc_info.value)
    
    def test_validate_customer_data_invalid_email(self, valid_customer_data):
        """Test validation with invalid email."""
        invalid_data = valid_customer_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        with pytest.raises(ValidationError) as exc_info:
            CustomerService._validate_customer_data(invalid_data)
        
        assert 'Invalid email format' in str(exc_info.value)
    
    def test_check_for_duplicates_email(self, valid_customer_data, mock_user_id):
        """Test duplicate checking for email."""
        with patch('app.services.customer_service.Customer') as mock_customer_class:
            mock_duplicate = Mock(spec=Customer)
            mock_duplicate.email = 'john.doe@example.com'
            mock_customer_class.query.filter_by.return_value.filter.return_value.first.return_value = mock_duplicate
            
            with pytest.raises(ValidationError) as exc_info:
                CustomerService._check_for_duplicates(valid_customer_data, mock_user_id)
            
            assert 'already exists' in str(exc_info.value)
    
    def test_is_valid_email_valid(self):
        """Test valid email validation."""
        assert CustomerService._is_valid_email('test@example.com') is True
        assert CustomerService._is_valid_email('user.name+tag@domain.co.uk') is True
    
    def test_is_valid_email_invalid(self):
        """Test invalid email validation."""
        assert CustomerService._is_valid_email('invalid-email') is False
        assert CustomerService._is_valid_email('@domain.com') is False
        assert CustomerService._is_valid_email('user@') is False
    
    def test_is_valid_phone_valid(self):
        """Test valid phone validation."""
        assert CustomerService._is_valid_phone('+1 (555) 123-4567') is True
        assert CustomerService._is_valid_phone('5551234567') is True
        assert CustomerService._is_valid_phone('+44 20 7123 4567') is True
    
    def test_is_valid_phone_invalid(self):
        """Test invalid phone validation."""
        assert CustomerService._is_valid_phone('abc') is False
        assert CustomerService._is_valid_phone('123') is False  # Too short
        assert CustomerService._is_valid_phone('x' * 25) is False  # Too long

"""
Customer Service - Handles all customer-related business logic.
Provides improved customer onboarding and management functionality.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from decimal import Decimal
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import ArgumentError
import logging

from app import db
from app.models import Customer, Order
from app.utils.exceptions import BusinessLogicError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class CustomerService:
    """Service class for customer management operations."""
    
    @staticmethod
    def create_customer(user_id: int, customer_data: Dict[str, Any]) -> Customer:
        """
        Create a new customer with validation and duplicate checking.
        
        Args:
            user_id: ID of the user creating the customer
            customer_data: Dictionary with customer details
            
        Returns:
            Customer: Created customer object
            
        Raises:
            ValidationError: If customer data is invalid
            BusinessLogicError: If business rules are violated
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("Invalid user ID")
            
        if not customer_data or not isinstance(customer_data, dict):
            raise ValidationError("Customer data is required and must be a dictionary")
            
        try:
            # Validate customer data
            CustomerService._validate_customer_data(customer_data, is_update=False)
            
            # Check for duplicates
            CustomerService._check_for_duplicates(customer_data, user_id)
            
            # Create customer
            customer = CustomerService._create_customer_entity(user_id, customer_data)
            
            db.session.add(customer)
            db.session.commit()
            
            logger.info(f"Created customer {customer.id} for user {user_id}")
            return customer
            
        except Exception as e:
            CustomerService._safe_rollback()
            logger.error(f"Failed to create customer for user {user_id}: {str(e)}")
            if isinstance(e, (ValidationError, BusinessLogicError)):
                raise
            raise BusinessLogicError(f"Failed to create customer: {str(e)}")

    @staticmethod
    def _safe_rollback():
        """Roll back while ignoring missing app context errors."""
        try:
            db.session.rollback()
        except RuntimeError:
            logger.debug("Rollback skipped because the session has no application context.")
    
    @staticmethod
    def update_customer(customer_id: int, user_id: int, 
                     customer_data: Dict[str, Any]) -> Customer:
        """
        Update an existing customer.
        
        Args:
            customer_id: ID of the customer to update
            user_id: ID of the user updating the customer
            customer_data: Dictionary with updated customer details
            
        Returns:
            Customer: Updated customer object
            
        Raises:
            NotFoundError: If customer doesn't exist or doesn't belong to user
            ValidationError: If update data is invalid
            BusinessLogicError: If business rules prevent update
        """
        try:
            customer = CustomerService._get_customer_for_user(customer_id, user_id)
            
            # Validate updated data
            CustomerService._validate_customer_data(customer_data, is_update=True)
            
            # Check for duplicates (excluding current customer)
            CustomerService._check_for_duplicates(customer_data, user_id, exclude_id=customer_id)
            
            # Update customer fields
            CustomerService._update_customer_fields(customer, customer_data)
            
            customer.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return customer
            
        except Exception as e:
            CustomerService._safe_rollback()
            if isinstance(e, (ValidationError, BusinessLogicError, NotFoundError)):
                raise
            raise BusinessLogicError(f"Failed to update customer: {str(e)}")
    
    @staticmethod
    def get_customer(customer_id: int, user_id: int) -> Customer:
        """
        Get a customer by ID for a specific user.
        
        Args:
            customer_id: ID of the customer
            user_id: ID of the user
            
        Returns:
            Customer: Customer object
            
        Raises:
            NotFoundError: If customer doesn't exist or doesn't belong to user
        """
        return CustomerService._get_customer_for_user(customer_id, user_id)
    
    @staticmethod
    def delete_customer(customer_id: int, user_id: int, 
                     force_delete: bool = False) -> bool:
        """
        Delete a customer (hard delete by default).
        
        Args:
            customer_id: ID of the customer to delete
            user_id: ID of the user deleting the customer
            force_delete: Whether to force delete (hard delete)
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            NotFoundError: If customer doesn't exist or doesn't belong to user
            BusinessLogicError: If customer has orders and force_delete is False
        """
        try:
            customer = CustomerService._get_customer_for_user(customer_id, user_id)
            
            # Check if customer has orders
            order_count = Order.query.filter_by(
                customer_id=customer_id,
                user_id=user_id
            ).count()
            if order_count > 0 and not force_delete:
                raise BusinessLogicError(
                    f"Cannot delete customer with {order_count} existing orders. "
                    "Use force_delete=True to override."
                )
            
            db.session.delete(customer)
            
            db.session.commit()
            return True
            
        except Exception as e:
            CustomerService._safe_rollback()
            if isinstance(e, (NotFoundError, BusinessLogicError)):
                raise
            raise BusinessLogicError(f"Failed to delete customer: {str(e)}")
    
    @staticmethod
    def toggle_customer_status(customer_id: int, user_id: int) -> Customer:
        """
        Toggle customer active status.
        
        Args:
            customer_id: ID of the customer
            user_id: ID of the user
            
        Returns:
            Customer: Updated customer object
            
        Raises:
            NotFoundError: If customer doesn't exist or doesn't belong to user
        """
        try:
            customer = CustomerService._get_customer_for_user(customer_id, user_id)
            customer.is_active = not customer.is_active
            customer.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            return customer
            
        except Exception as e:
            CustomerService._safe_rollback()
            if isinstance(e, NotFoundError):
                raise
            raise BusinessLogicError(f"Failed to toggle customer status: {str(e)}")
    
    @staticmethod
    def search_customers(user_id: int, query: str, 
                        filters: Optional[Dict[str, Any]] = None,
                        limit: int = 20) -> List[Customer]:
        """
        Search customers with advanced filtering.
        
        Args:
            user_id: ID of the user
            query: Search query string
            filters: Optional dictionary of filters
            limit: Maximum number of results
            
        Returns:
            List[Customer]: List of matching customers
        """
        try:
            # Build base query
            base_query = Customer.query.filter_by(user_id=user_id)
            
            # Apply search
            if query and len(query.strip()) >= 2:
                search_term = f"%{query.strip()}%"
                columns = (
                    Customer.name,
                    Customer.email,
                    Customer.phone,
                    Customer.company
                )
                column_filters = []
                for column in columns:
                    try:
                        column_filters.append(column.ilike(search_term))
                    except Exception:
                        column_filters = []
                        break

                applied_search = False
                if column_filters:
                    try:
                        base_query = base_query.filter(or_(*column_filters))
                        applied_search = True
                    except ArgumentError:
                        applied_search = False
                if not applied_search and column_filters:
                    base_query = base_query.filter(column_filters[0])
            
            # Apply additional filters
            if filters:
                base_query = CustomerService._apply_customer_filters(base_query, filters)
            
            # Order and limit
            customers = base_query.order_by(
                func.similarity(Customer.name, query).desc() if query else Customer.name
            ).limit(limit).all()
            
            return customers
            
        except Exception as e:
            raise BusinessLogicError(f"Failed to search customers: {str(e)}")
    
    @staticmethod
    def get_customers_for_user(user_id: int, 
                              filters: Optional[Dict[str, Any]] = None,
                              page: int = 1, per_page: int = 20) -> Tuple[List[Customer], int]:
        """
        Get customers for a user with optional filtering and pagination.
        
        Args:
            user_id: ID of the user
            filters: Optional dictionary of filters
            page: Page number for pagination
            per_page: Number of items per page
            
        Returns:
            Tuple[List[Customer], int]: List of customers and total count
        """
        try:
            query = Customer.query.filter_by(user_id=user_id)
            
            # Apply filters
            if filters:
                query = CustomerService._apply_customer_filters(query, filters)
            
            # Order by name
            query = query.order_by(Customer.name.asc())
            
            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return pagination.items, pagination.total
            
        except Exception as e:
            raise BusinessLogicError(f"Failed to get customers: {str(e)}")
    
    @staticmethod
    def get_recent_customers(user_id: int, limit: int = 5) -> List[Customer]:
        """
        Get recently used customers based on order history.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of customers to return
            
        Returns:
            List[Customer]: List of recent customers
        """
        try:
            last_seen = func.max(Order.updated_at).label('last_seen')
            recent_customer_entries = (
                db.session.query(Order.customer_id, last_seen)
                .filter_by(user_id=user_id)
                .group_by(Order.customer_id)
                .order_by(last_seen.desc())
                .limit(limit)
                .all()
            )

            customer_ids = [
                customer_id for customer_id, _ in recent_customer_entries if customer_id
            ]
            
            if not customer_ids:
                return []
            
            # Get customer details
            customers = Customer.query.filter(
                Customer.id.in_(customer_ids),
                Customer.user_id == user_id,
                Customer.is_active == True
            ).all()
            
            # Sort by most recent order
            def _sort_key(customer: Customer) -> int:
                try:
                    return customer_ids.index(customer.id)
                except ValueError:
                    return len(customer_ids)
            customers.sort(key=_sort_key)
            
            return customers[:limit]
            
        except Exception as e:
            raise BusinessLogicError(f"Failed to get recent customers: {str(e)}")
    
    @staticmethod
    def get_customer_statistics(customer_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a customer.
        
        Args:
            customer_id: ID of the customer
            user_id: ID of the user
            
        Returns:
            Dict[str, Any]: Customer statistics
            
        Raises:
            NotFoundError: If customer doesn't exist or doesn't belong to user
        """
        try:
            customer = CustomerService._get_customer_for_user(customer_id, user_id)
            
            # Order statistics
            orders = Order.query.filter_by(
                customer_id=customer_id,
                user_id=user_id
            )
            
            total_orders = orders.count()
            completed_orders = orders.filter(Order.status == Order.STATUS_COMPLETED).count()
            total_spent = db.session.query(func.sum(Order.total_amount))\
                .filter_by(
                    customer_id=customer_id,
                    user_id=user_id,
                    status=Order.STATUS_COMPLETED
                )\
                .scalar() or Decimal('0')
            
            # Recent activity
            latest_order = orders.order_by(Order.created_at.desc()).first()
            last_order_date = latest_order.created_at if latest_order else None
            
            # Average order value
            avg_order_value = total_spent / completed_orders if completed_orders > 0 else Decimal('0')
            
            return {
                'customer': customer,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'total_spent': float(total_spent),
                'average_order_value': float(avg_order_value),
                'last_order_date': last_order_date.isoformat() if last_order_date else None,
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            }
            
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BusinessLogicError(f"Failed to get customer statistics: {str(e)}")
    
    @staticmethod
    def import_customers(user_id: int, customers_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Import multiple customers with validation.
        
        Args:
            user_id: ID of the user importing customers
            customers_data: List of customer data dictionaries
            
        Returns:
            Dict[str, Any]: Import results with success/failure counts
        """
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'imported_customers': []
        }
        
        for index, customer_data in enumerate(customers_data):
            try:
                customer = CustomerService.create_customer(user_id, customer_data)
                results['success_count'] += 1
                results['imported_customers'].append({
                    'index': index,
                    'customer_id': customer.id,
                    'name': customer.name
                })
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'index': index,
                    'error': str(e),
                    'data': customer_data
                })
        
        return results
    
    # Private helper methods
    
    @staticmethod
    def _validate_customer_data(customer_data: Dict[str, Any], is_update: bool = False) -> None:
        """Validate customer data."""
        if not customer_data:
            raise ValidationError("Customer data is required")
        
        # Name validation
        name = customer_data.get('name', '').strip()
        if not name or len(name) < 2:
            raise ValidationError("Name must be at least 2 characters long")
        
        if len(name) > 120:
            raise ValidationError("Name cannot exceed 120 characters")
        
        # Email validation
        email = customer_data.get('email', '').strip()
        if email:
            if not CustomerService._is_valid_email(email):
                raise ValidationError("Invalid email format")
            if len(email) > 120:
                raise ValidationError("Email cannot exceed 120 characters")
        
        # Phone validation
        phone = customer_data.get('phone', '').strip()
        if phone:
            if not CustomerService._is_valid_phone(phone):
                raise ValidationError("Invalid phone number format")
            if len(phone) > 20:
                raise ValidationError("Phone cannot exceed 20 characters")
        
        # Other field validations
        if customer_data.get('company') and len(customer_data['company']) > 120:
            raise ValidationError("Company cannot exceed 120 characters")
        
        if customer_data.get('address') and len(customer_data['address']) > 255:
            raise ValidationError("Address cannot exceed 255 characters")
        
        if customer_data.get('city') and len(customer_data['city']) > 100:
            raise ValidationError("City cannot exceed 100 characters")
        
        if customer_data.get('state') and len(customer_data['state']) > 100:
            raise ValidationError("State cannot exceed 100 characters")
        
        if customer_data.get('postal_code') and len(customer_data['postal_code']) > 20:
            raise ValidationError("Postal code cannot exceed 20 characters")
        
        if customer_data.get('tax_id') and len(customer_data['tax_id']) > 50:
            raise ValidationError("Tax ID cannot exceed 50 characters")
    
    @staticmethod
    def _check_for_duplicates(customer_data: Dict[str, Any], user_id: int, 
                           exclude_id: Optional[int] = None) -> None:
        """Check for duplicate customers."""
        email = customer_data.get('email', '').strip().lower()
        phone = customer_data.get('phone', '').strip()
        
        # Build query for duplicates
        duplicate_query = Customer.query.filter_by(user_id=user_id)
        
        conditions = []
        if email:
            conditions.append(Customer.email == email)
        if phone:
            conditions.append(Customer.phone == phone)
        
        if conditions:
            duplicate_query = duplicate_query.filter(or_(*conditions))
            
            if exclude_id:
                duplicate_query = duplicate_query.filter(Customer.id != exclude_id)
            
            duplicate = duplicate_query.first()
            if duplicate:
                if email and duplicate.email and duplicate.email.lower() == email:
                    raise ValidationError(f"A customer with email '{email}' already exists")
                if phone and duplicate.phone == phone:
                    raise ValidationError(f"A customer with phone '{phone}' already exists")
    
    @staticmethod
    def _create_customer_entity(user_id: int, customer_data: Dict[str, Any]) -> Customer:
        """Create customer entity from data."""
        return Customer(
            user_id=user_id,
            name=customer_data['name'].strip(),
            email=customer_data.get('email', '').strip().lower() or None,
            phone=customer_data.get('phone', '').strip() or None,
            company=customer_data.get('company', '').strip() or None,
            address=customer_data.get('address', '').strip() or None,
            address2=customer_data.get('address2', '').strip() or None,
            city=customer_data.get('city', '').strip() or None,
            state=customer_data.get('state', '').strip() or None,
            postal_code=customer_data.get('postal_code', '').strip() or None,
            country=customer_data.get('country', 'United States').strip(),
            tax_id=customer_data.get('tax_id', '').strip() or None,
            is_active=customer_data.get('is_active', True),
            notes=customer_data.get('notes', '').strip() or None
        )
    
    @staticmethod
    def _get_customer_for_user(customer_id: int, user_id: int) -> Customer:
        """Get customer and validate it belongs to user."""
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        if not customer:
            raise NotFoundError(f"Customer with ID {customer_id} not found")
        return customer
    
    @staticmethod
    def _update_customer_fields(customer: Customer, customer_data: Dict[str, Any]) -> None:
        """Update customer fields from data."""
        updatable_fields = [
            'name', 'email', 'phone', 'company', 'address', 'address2',
            'city', 'state', 'postal_code', 'country', 'tax_id', 
            'is_active', 'notes'
        ]
        
        for field in updatable_fields:
            if field in customer_data:
                value = customer_data[field]
                if field == 'email' and value:
                    value = value.lower().strip()
                elif isinstance(value, str):
                    value = value.strip() or None
                setattr(customer, field, value)
    
    @staticmethod
    def _apply_customer_filters(query, filters: Dict[str, Any]):
        """Apply filters to customer query."""
        if filters.get('is_active') is not None:
            query = query.filter(Customer.is_active == filters['is_active'])
        
        if filters.get('has_orders') is not None:
            if filters['has_orders']:
                query = query.filter(Customer.orders.any())
            else:
                query = query.filter(~Customer.orders.any())
        
        if filters.get('country'):
            query = query.filter(Customer.country.ilike(f"%{filters['country']}%"))
        
        if filters.get('city'):
            query = query.filter(Customer.city.ilike(f"%{filters['city']}%"))
        
        return query
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email, re.IGNORECASE) is not None
    
    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        """Validate phone number format."""
        # Basic phone validation - allows digits, spaces, hyphens, plus, parentheses
        pattern = r'^[\d\s\-+\(\)]{6,20}$'
        return re.match(pattern, phone) is not None

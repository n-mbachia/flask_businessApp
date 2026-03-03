"""
Order Service - Handles all order-related business logic.
Separates business logic from routes and models for better maintainability.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app import db
from app.models import Order, OrderItem, Customer, Product
from app.services.inventory_service import InventoryService
from app.utils.exceptions import BusinessLogicError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class OrderService:
    """Service class for order management operations."""
    
    @staticmethod
    def create_order(user_id: int, order_data: Dict[str, Any], 
                   items_data: List[Dict[str, Any]], 
                   update_inventory: bool = False) -> Order:
        """
        Create a new order with validation and inventory management.
        
        Args:
            user_id: ID of the user creating the order
            order_data: Dictionary with order details
            items_data: List of dictionaries with order item details
            update_inventory: Whether to update inventory immediately
            
        Returns:
            Order: Created order object
            
        Raises:
            ValidationError: If order data is invalid
            BusinessLogicError: If business rules are violated
            NotFoundError: If customer or products are not found
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("Invalid user ID")
            
        if not order_data or not isinstance(order_data, dict):
            raise ValidationError("Order data is required and must be a dictionary")
            
        if not items_data or not isinstance(items_data, list):
            raise ValidationError("Items data is required and must be a list")
            
        try:
            # Validate basic order data
            OrderService._validate_order_data(order_data, items_data)
            
            # Validate customer exists and belongs to user
            customer = OrderService._get_and_validate_customer(
                order_data.get('customer_id'), user_id
            )
            
            # Validate items and inventory
            validated_items = OrderService._validate_and_prepare_items(
                items_data, user_id, update_inventory
            )
            
            # Create order
            order = OrderService._create_order_entity(
                user_id, order_data, customer, validated_items
            )
            
            # Update inventory if requested
            if update_inventory and order.status == Order.STATUS_COMPLETED:
                OrderService._update_inventory_for_order(
                    order, user_id, validated_items
                )
            
            db.session.commit()
            return order
            
        except Exception as e:
            db.session.rollback()
            if isinstance(e, (ValidationError, BusinessLogicError, NotFoundError)):
                raise
            raise BusinessLogicError(f"Failed to create order: {str(e)}")
    
    @staticmethod
    def update_order(order_id: int, user_id: int, 
                   order_data: Dict[str, Any], 
                   items_data: Optional[List[Dict[str, Any]]] = None) -> Order:
        """
        Update an existing order.
        
        Args:
            order_id: ID of the order to update
            user_id: ID of the user updating the order
            order_data: Dictionary with updated order details
            items_data: Optional list of updated items
            
        Returns:
            Order: Updated order object
            
        Raises:
            NotFoundError: If order doesn't exist or doesn't belong to user
            ValidationError: If update data is invalid
            BusinessLogicError: If business rules prevent update
        """
        try:
            order = OrderService._get_order_for_user(order_id, user_id)
            
            # Check if order can be updated
            OrderService._validate_order_update_allowed(order)
            
            # Update order fields
            OrderService._update_order_fields(order, order_data)
            
            # Update items if provided
            if items_data is not None:
                OrderService._update_order_items(order, items_data, user_id)
            
            db.session.commit()
            return order
            
        except Exception as e:
            db.session.rollback()
            if isinstance(e, (ValidationError, BusinessLogicError, NotFoundError)):
                raise
            raise BusinessLogicError(f"Failed to update order: {str(e)}")
    
    @staticmethod
    def complete_order(order_id: int, user_id: int) -> Order:
        """
        Mark an order as completed and update inventory.
        
        Args:
            order_id: ID of the order to complete
            user_id: ID of the user completing the order
            
        Returns:
            Order: Updated order object
            
        Raises:
            NotFoundError: If order doesn't exist or doesn't belong to user
            BusinessLogicError: If order cannot be completed
        """
        try:
            order = OrderService._get_order_for_user(order_id, user_id)
            
            if order.status == Order.STATUS_COMPLETED:
                return order  # Already completed
            
            if order.status == Order.STATUS_CANCELLED:
                raise BusinessLogicError("Cannot complete a cancelled order")
            
            # Mark as completed (this will update inventory)
            order.mark_as_completed(db.session)
            
            db.session.commit()
            return order
            
        except Exception as e:
            db.session.rollback()
            if isinstance(e, (NotFoundError, BusinessLogicError)):
                raise
            raise BusinessLogicError(f"Failed to complete order: {str(e)}")
    
    @staticmethod
    def cancel_order(order_id: int, user_id: int) -> Order:
        """
        Cancel an order and return items to inventory if completed.
        
        Args:
            order_id: ID of the order to cancel
            user_id: ID of the user cancelling the order
            
        Returns:
            Order: Updated order object
            
        Raises:
            NotFoundError: If order doesn't exist or doesn't belong to user
            BusinessLogicError: If order cannot be cancelled
        """
        try:
            order = OrderService._get_order_for_user(order_id, user_id)
            
            if order.status == Order.STATUS_CANCELLED:
                return order  # Already cancelled
            
            if order.status in [Order.STATUS_PROCESSING, Order.STATUS_COMPLETED]:
                # Return items to inventory if order was completed
                if order.status == Order.STATUS_COMPLETED:
                    OrderService._return_inventory_for_order(order, user_id)
            
            order.status = Order.STATUS_CANCELLED
            order.updated_at = datetime.utcnow()
            
            db.session.commit()
            return order
            
        except Exception as e:
            db.session.rollback()
            if isinstance(e, (NotFoundError, BusinessLogicError)):
                raise
            raise BusinessLogicError(f"Failed to cancel order: {str(e)}")
    
    @staticmethod
    def get_orders_for_user(user_id: int, filters: Optional[Dict[str, Any]] = None,
                          page: int = 1, per_page: int = 20) -> Tuple[List[Order], int]:
        """
        Get orders for a user with optional filtering and pagination.
        
        Args:
            user_id: ID of the user
            filters: Optional dictionary of filters
            page: Page number for pagination
            per_page: Number of items per page
            
        Returns:
            Tuple[List[Order], int]: List of orders and total count
        """
        query = Order.query.filter_by(user_id=user_id)
        
        # Apply filters
        if filters:
            query = OrderService._apply_order_filters(query, filters)
        
        # Order by most recent
        query = query.order_by(Order.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return pagination.items, pagination.total
    
    @staticmethod
    def calculate_order_totals(items_data: List[Dict[str, Any]], 
                           tax_rate: Decimal = Decimal('0'),
                           shipping_amount: Decimal = Decimal('0'),
                           discount_amount: Decimal = Decimal('0')) -> Dict[str, Decimal]:
        """
        Calculate order totals based on items and adjustments.
        
        Args:
            items_data: List of item dictionaries with quantity and unit_price
            tax_rate: Tax rate as decimal (e.g., 0.16 for 16%)
            shipping_amount: Shipping cost
            discount_amount: Discount amount
            
        Returns:
            Dict[str, Decimal]: Calculated totals
        """
        try:
            # Calculate subtotal
            subtotal = Decimal('0')
            for item in items_data:
                if item.get('product_id') and item.get('quantity') and item.get('unit_price'):
                    quantity = Decimal(str(item['quantity']))
                    unit_price = Decimal(str(item['unit_price']))
                    subtotal += quantity * unit_price
            
            # Calculate tax
            tax_amount = subtotal * tax_rate
            
            # Calculate total
            total = (subtotal + tax_amount + shipping_amount) - discount_amount
            
            return {
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'shipping_amount': shipping_amount,
                'discount_amount': discount_amount,
                'total': max(Decimal('0'), total)  # Ensure non-negative
            }
            
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid numeric data in order calculation: {str(e)}")
    
    # Private helper methods
    
    @staticmethod
    def _validate_order_data(order_data: Dict[str, Any], 
                           items_data: List[Dict[str, Any]]) -> None:
        """Validate basic order data."""
        if not order_data:
            raise ValidationError("Order data is required")
        
        if not items_data or len(items_data) == 0:
            raise ValidationError("At least one order item is required")
        
        # Check if any item has valid data
        valid_items = [item for item in items_data if item.get('product_id')]
        if not valid_items:
            raise ValidationError("At least one valid order item is required")

    @staticmethod
    def _normalize_source(source: Optional[str]) -> str:
        """Normalize the incoming source to a supported value."""
        if not source:
            return Order.SOURCE_MANUAL
        normalized = str(source).strip().lower()
        if normalized not in Order.SOURCE_CHOICES:
            return Order.SOURCE_MANUAL
        return normalized
    
    @staticmethod
    def _get_and_validate_customer(customer_id: Optional[int], user_id: int) -> Optional[Customer]:
        """Get and validate customer belongs to user."""
        if not customer_id:
            return None
        
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        if not customer:
            raise NotFoundError(f"Customer with ID {customer_id} not found")
        
        if not customer.is_active:
            raise ValidationError("Selected customer is not active")
        
        return customer
    
    @staticmethod
    def _validate_and_prepare_items(items_data: List[Dict[str, Any]], 
                                 user_id: int, 
                                 check_inventory: bool = True) -> List[Dict[str, Any]]:
        """Validate and prepare order items."""
        validated_items = []
        
        for item_data in items_data:
            if not item_data.get('product_id'):
                continue
            
            # Validate product exists and belongs to user
            product = Product.query.filter_by(
                id=item_data['product_id'], 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not product:
                raise NotFoundError(f"Product with ID {item_data['product_id']} not found")
            
            # Validate quantity
            try:
                quantity = Decimal(str(item_data.get('quantity', 0)))
                if quantity <= 0:
                    raise ValidationError("Quantity must be greater than 0")
            except (InvalidOperation, ValueError):
                raise ValidationError("Invalid quantity value")
            
            # Get unit price (from form or product)
            unit_price = Decimal(str(item_data.get('unit_price', product.selling_price_per_unit or 0)))
            
            # Calculate subtotal
            subtotal = quantity * unit_price
            
            validated_items.append({
                'product_id': product.id,
                'product': product,
                'quantity': float(quantity),  # Convert to float for database
                'unit_price': unit_price,
                'subtotal': subtotal,
                'notes': item_data.get('notes', '')
            })
        
        # Check inventory if required
        if check_inventory and validated_items:
            is_valid, results = InventoryService.validate_order_items(
                db.session, user_id, validated_items
            )
            if not is_valid:
                error_messages = [
                    result['message'] for result in results if not result['success']
                ]
                raise ValidationError(f"Insufficient inventory: {'; '.join(error_messages)}")
        
        return validated_items
    
    @staticmethod
    def _create_order_entity(user_id: int, order_data: Dict[str, Any], 
                           customer: Optional[Customer], 
                           validated_items: List[Dict[str, Any]]) -> Order:
        """Create the order entity with items."""
        # Create order
        source_value = OrderService._normalize_source(order_data.get('source'))
        order = Order(
            user_id=user_id,
            customer_id=customer.id if customer else None,
            order_date=datetime.utcnow(),
            status=order_data.get('status', Order.STATUS_PENDING),
            payment_status=order_data.get('payment_status', Order.PAYMENT_UNPAID),
            total_amount=Decimal(str(order_data.get('total_amount', 0))),
            is_recurring=order_data.get('is_recurring', False),
            notes=order_data.get('notes', ''),
            source=source_value
        )
        
        db.session.add(order)
        db.session.flush()  # Get the order ID
        
        # Create order items
        for item_data in validated_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                subtotal=item_data['subtotal'],
                notes=item_data['notes']
            )
            db.session.add(order_item)
        
        return order
    
    @staticmethod
    def _update_inventory_for_order(order: Order, user_id: int, 
                                  validated_items: List[Dict[str, Any]]) -> None:
        """Update inventory for completed order."""
        inventory_updates = []
        for item in validated_items:
            inventory_updates.append({
                'product_id': item['product_id'],
                'quantity_change': -item['quantity']  # Negative for sales
            })
        
        success, results = InventoryService.update_inventory_levels(
            db.session, user_id, inventory_updates,
            reference_type='order', reference_id=order.id,
            notes=f'Order #{order.id} completed'
        )
        
        if not success:
            error_messages = [
                result['message'] for result in results if not result['success']
            ]
            raise BusinessLogicError(f"Inventory update failed: {'; '.join(error_messages)}")
    
    @staticmethod
    def _return_inventory_for_order(order: Order, user_id: int) -> None:
        """Return items to inventory when cancelling a completed order."""
        inventory_updates = []
        for item in order.items:
            inventory_updates.append({
                'product_id': item.product_id,
                'quantity_change': float(item.quantity)  # Positive to return
            })
        
        success, results = InventoryService.update_inventory_levels(
            db.session, user_id, inventory_updates,
            reference_type='order_cancel', reference_id=order.id,
            notes=f'Order #{order.id} cancelled - items returned'
        )
        
        if not success:
            error_messages = [
                result['message'] for result in results if not result['success']
            ]
            raise BusinessLogicError(f"Inventory return failed: {'; '.join(error_messages)}")
    
    @staticmethod
    def _get_order_for_user(order_id: int, user_id: int) -> Order:
        """Get order and validate it belongs to user."""
        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        if not order:
            raise NotFoundError(f"Order with ID {order_id} not found")
        return order
    
    @staticmethod
    def _validate_order_update_allowed(order: Order) -> None:
        """Validate that order can be updated."""
        if order.status == Order.STATUS_CANCELLED:
            raise BusinessLogicError("Cannot update a cancelled order")
        
        if order.status == Order.STATUS_COMPLETED:
            raise BusinessLogicError("Cannot update a completed order")
    
    @staticmethod
    def _update_order_fields(order: Order, order_data: Dict[str, Any]) -> None:
        """Update order fields from data."""
        updatable_fields = [
            'customer_id', 'status', 'payment_status', 
            'is_recurring', 'notes', 'source'
        ]
        
        for field in updatable_fields:
            if field in order_data:
                setattr(order, field, order_data[field])
        
        order.updated_at = datetime.utcnow()
    
    @staticmethod
    def _update_order_items(order: Order, items_data: List[Dict[str, Any]], 
                          user_id: int) -> None:
        """Update order items."""
        # Remove existing items
        OrderItem.query.filter_by(order_id=order.id).delete()
        
        # Add new items
        validated_items = OrderService._validate_and_prepare_items(
            items_data, user_id, check_inventory=False  # Don't check inventory for updates
        )
        
        for item_data in validated_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                subtotal=item_data['subtotal'],
                notes=item_data['notes']
            )
            db.session.add(order_item)
    
    @staticmethod
    def _apply_order_filters(query, filters: Dict[str, Any]):
        """Apply filters to order query."""
        if filters.get('status'):
            query = query.filter(Order.status == filters['status'])
        
        if filters.get('customer_id'):
            query = query.filter(Order.customer_id == filters['customer_id'])
        
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
                query = query.filter(Order.order_date >= date_from)
            except ValueError:
                pass
        
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d')
                query = query.filter(Order.order_date <= date_to)
            except ValueError:
                pass
        
        if filters.get('search_query'):
            search = f"%{filters['search_query']}%"
            query = query.join(Customer).filter(
                or_(
                    Order.id.like(search.replace('%', '') + '%'),
                    Customer.name.ilike(search),
                    Customer.email.ilike(search)
                )
            )
        
        return query

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, CheckConstraint, event, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.models.base import BaseModelMixin

if TYPE_CHECKING:
    from .users import User
    from .customers import Customer
    from .order_item import OrderItem

class Order(db.Model, BaseModelMixin):
    """
    Represents a customer order.
    """
    __tablename__ = 'orders'
    
    # Status and payment status constants
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    PAYMENT_UNPAID = 'unpaid'
    PAYMENT_PARTIAL = 'partial'
    PAYMENT_PAID = 'paid'
    PAYMENT_REFUNDED = 'refunded'
    PAYMENT_FAILED = 'failed'
    
    # Status choices for forms
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled')
    ]
    
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_UNPAID, 'Unpaid'),
        (PAYMENT_PARTIAL, 'Partially Paid'),
        (PAYMENT_PAID, 'Paid'),
        (PAYMENT_REFUNDED, 'Refunded'),
        (PAYMENT_FAILED, 'Payment Failed')
    ]
    
    SOURCE_MANUAL = 'manual'
    SOURCE_STOREFRONT = 'storefront'
    SOURCE_CHOICES = frozenset({SOURCE_MANUAL, SOURCE_STOREFRONT})

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey('customers.id'), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    order_number: Mapped[str] = mapped_column(db.String(50), unique=True, index=True)
    order_date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(db.String(20), default=STATUS_PENDING, nullable=False)
    payment_status: Mapped[str] = mapped_column(db.String(20), default=PAYMENT_UNPAID, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    source: Mapped[str] = mapped_column(
        db.String(32),
        default=SOURCE_MANUAL,
        nullable=False,
        server_default=text(f"'{SOURCE_MANUAL}'")
    )
    is_recurring: Mapped[bool] = mapped_column(db.Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(db.Text)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # Relationships
    items: Mapped[List['OrderItem']] = relationship("app.models.order_item.OrderItem", back_populates='order', cascade='all, delete-orphan')
    user: Mapped['User'] = relationship('User', back_populates='orders')
    customer: Mapped['Customer'] = relationship('Customer', back_populates='orders')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'cancelled')", name='valid_status'),
        CheckConstraint("payment_status IN ('unpaid', 'partial', 'paid', 'refunded', 'failed')", name='valid_payment_status'),
        CheckConstraint('total_amount >= 0', name='non_negative_total'),
        CheckConstraint('subtotal >= 0', name='non_negative_subtotal'),
        CheckConstraint('tax_amount >= 0', name='non_negative_tax'),
        CheckConstraint('shipping_amount >= 0', name='non_negative_shipping'),
        CheckConstraint('discount_amount >= 0', name='non_negative_discount'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, 'source', None):
            self.source = self.SOURCE_MANUAL
        if not self.order_number:
            self.order_number = self._generate_order_number()
    
    def _generate_order_number(self) -> str:
        """Generate a unique order number."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f'ORD-{timestamp}'
    
    def calculate_total(self) -> Decimal:
        """Calculate subtotal and total amount based on order items and adjustments."""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.total_amount = (
            self.subtotal
            + (self.tax_amount or Decimal('0.00'))
            + (self.shipping_amount or Decimal('0.00'))
            - (self.discount_amount or Decimal('0.00'))
        )
        return self.total_amount
    
    def update_status(self, new_status: str) -> bool:
        """Update the order status if valid."""
        if new_status in dict(self.STATUS_CHOICES):
            self.status = new_status
            return True
        return False
    
    def update_payment_status(self, new_status: str) -> bool:
        """Update the payment status if valid."""
        if new_status in dict(self.PAYMENT_STATUS_CHOICES):
            self.payment_status = new_status
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convert order to dictionary."""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'order_date': self.order_date.isoformat(),
            'status': self.status,
            'status_display': dict(self.STATUS_CHOICES).get(self.status, self.status),
            'payment_status': self.payment_status,
            'payment_status_display': dict(self.PAYMENT_STATUS_CHOICES).get(self.payment_status, self.payment_status),
            'subtotal': float(self.subtotal) if self.subtotal else 0.0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0.0,
            'shipping_amount': float(self.shipping_amount) if self.shipping_amount else 0.0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0.0,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'is_recurring': self.is_recurring,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source': self.source,
            'source_display': 'Storefront' if self.source == self.SOURCE_STOREFRONT else 'Manual entry',
            'items': [item.to_dict() for item in self.items]
        }
    
    def mark_as_completed(self, db_session):
        """Mark order as completed and update inventory.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.status == self.STATUS_COMPLETED:
            return True  # Already completed
            
        # Update inventory
        from app.services.inventory_service import InventoryService

        # Skip inventory update if movements already exist for this order
        if InventoryService.has_reference_movements(
            db_session,
            reference_id=self.id,
            reference_types=['order', 'storefront']
        ):
            self.status = self.STATUS_COMPLETED
            self.updated_at = datetime.utcnow()
            return True
        
        # Prepare inventory updates
        inventory_updates = []
        for item in self.items:
            inventory_updates.append({
                'product_id': item.product_id,
                'quantity_change': -float(item.quantity)  # Negative for sales
            })
        
        # Update inventory
        success, results = InventoryService.update_inventory_levels(
            db_session,
            self.user_id,
            inventory_updates,
            reference_type='order',
            reference_id=self.id,
            notes=f'Order #{self.id} completed'
        )
        
        if not success:
            error_messages = [
                result['message'] 
                for result in results 
                if not result.get('success', True)
            ]
            raise Exception("Inventory update failed: " + "; ".join(error_messages))
        
        # Update order status
        self.status = self.STATUS_COMPLETED
        self.updated_at = datetime.utcnow()
        return True

    def __repr__(self) -> str:
        return f'<Order {self.order_number} - {self.status} ({self.source})>'

# Event listeners
@event.listens_for(Order, 'before_update')
def update_order_totals(mapper, connection, target):
    """Update order totals before saving."""
    target.calculate_total()

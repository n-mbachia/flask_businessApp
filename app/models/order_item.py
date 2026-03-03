# app/models/order_item.py

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import event, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app import db
from app.models.base import BaseModelMixin

if TYPE_CHECKING:
    from .inventory_lots import InventoryLot
    from .orders import Order
    from .products import Product

class OrderItem(db.Model, BaseModelMixin):
    """
    Represents a single product line inside an order.
    
    Attributes:
        id (int): Primary key of the order item.
        order_id (int): Foreign key referencing the parent order.
        product_id (int): Foreign key referencing the product sold.
        quantity (int): Quantity of the product ordered.
        unit_price (Decimal): Price per unit at the time of the order.
        subtotal (Decimal): Computed as quantity * unit_price.
        lot_id (int, optional): References the inventory lot used.
        notes (str, optional): Additional notes about this order item.
    """
    __tablename__ = 'order_items'

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    quantity: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(db.Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(db.Numeric(14, 2), nullable=False)  # Increased precision for calculations
    lot_id: Mapped[Optional[int]] = mapped_column(ForeignKey('inventory_lot.id'), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, 
        default=db.func.current_timestamp(), 
        onupdate=db.func.current_timestamp(),
        nullable=False
    )
    
    # Relationships - using string-based forward references to avoid circular imports
    order: Mapped['Order'] = relationship('Order', back_populates='items')
    product: Mapped['Product'] = relationship('Product', back_populates='order_items')
    lot: Mapped[Optional['InventoryLot']] = relationship('InventoryLot', back_populates='order_items')
    
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='positive_quantity'),
        db.CheckConstraint('unit_price >= 0', name='non_negative_unit_price'),
        db.CheckConstraint('subtotal >= 0', name='non_negative_subtotal'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_subtotal()
    
    def __repr__(self):
        return f'<OrderItem {self.id} - {self.quantity}x {self.product_id} @ {self.unit_price} = {self.subtotal}>'
    
    def calculate_subtotal(self) -> None:
        """Calculate the subtotal for this order item."""
        if self.quantity is not None and self.unit_price is not None:
            self.subtotal = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
    
    @validates('quantity')
    def validate_quantity(self, key, quantity):
        if quantity <= 0:
            raise ValueError('Quantity must be greater than zero')
        return quantity
    
    @validates('unit_price')
    def validate_unit_price(self, key, unit_price):
        if unit_price < 0:
            raise ValueError('Unit price cannot be negative')
        return unit_price
    
    def update_quantity(self, new_quantity: int, save: bool = True) -> None:
        """Update the quantity and recalculate the subtotal."""
        if new_quantity < 1:
            raise ValueError("Quantity must be at least 1")
        self.quantity = new_quantity
        self.calculate_subtotal()
        if save:
            self.save()
    
    def update_unit_price(self, new_price: Decimal, save: bool = True) -> None:
        """Update the unit price and recalculate the subtotal."""
        if new_price < 0:
            raise ValueError("Unit price cannot be negative")
        self.unit_price = new_price
        self.calculate_subtotal()
        if save:
            self.save()
    
    def to_dict(self) -> dict:
        """Convert the order item to a dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price is not None else 0.0,
            'subtotal': float(self.subtotal) if self.subtotal is not None else 0.0,
            'lot_id': self.lot_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Event listeners
@event.listens_for(OrderItem, 'before_insert')
@event.listens_for(OrderItem, 'before_update')
def calculate_subtotal_before_save(mapper, connection, target):
    """Ensure subtotal is calculated before saving."""
    target.calculate_subtotal()

@event.listens_for(OrderItem, 'after_insert')
@event.listens_for(OrderItem, 'after_update')
@event.listens_for(OrderItem, 'after_delete')
def update_order_total_after_change(mapper, connection, target):
    """Update the parent order's total when an item changes."""
    if target.order_id:
        # Use connection.execute to avoid session conflicts during flush
        connection.execute(
            db.text("""
                UPDATE orders 
                SET subtotal = (
                    SELECT COALESCE(SUM(subtotal), 0.00)
                    FROM order_items 
                    WHERE order_id = :order_id
                ),
                total_amount = (
                    SELECT COALESCE(SUM(subtotal), 0.00)
                    FROM order_items 
                    WHERE order_id = :order_id
                ) + COALESCE(tax_amount, 0.00)
                  + COALESCE(shipping_amount, 0.00)
                  - COALESCE(discount_amount, 0.00)
                WHERE id = :order_id
            """),
            {'order_id': target.order_id}
        )

"""
Inventory Log Model

This module defines the InventoryLog model for tracking inventory changes.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Index, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app import db
from app.models.base import BaseModelMixin

if TYPE_CHECKING:
    from .products import Product
    from .users import User

class InventoryLog(db.Model, BaseModelMixin):
    """
    Tracks all inventory changes for auditing and reporting purposes.
    """
    __tablename__ = 'inventory_logs'
    
    # Reference types for different inventory operations
    REF_ORDER = 'order'
    REF_RETURN = 'return'
    REF_ADJUSTMENT = 'adjustment'
    REF_PURCHASE = 'purchase'
    REF_OTHER = 'other'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Reference information
    reference_type = Column(String(20), nullable=False, index=True)  # e.g., 'order', 'return', 'adjustment'
    reference_id = Column(Integer, index=True)  # ID of the related document
    
    # Quantity information
    quantity_change = Column(Float, nullable=False)  # Positive for additions, negative for subtractions
    quantity_before = Column(Float, nullable=False)
    quantity_after = Column(Float, nullable=False)
    
    # Cost information (optional)
    unit_cost = Column(Numeric(10, 2), nullable=True, default=None)  # Cost per unit at the time of movement
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    product: Mapped['Product'] = relationship('Product', back_populates='inventory_logs')
    user: Mapped['User'] = relationship('User', back_populates='inventory_logs')
    
    __table_args__ = (
        # Index for common query patterns
        Index('idx_inventory_log_product_created', 'product_id', 'created_at'),
        Index('idx_inventory_log_reference', 'reference_type', 'reference_id'),
        Index('idx_inventory_log_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<InventoryLog {self.id}: Product {self.product_id} changed by {self.quantity_change}>"
    
    @classmethod
    def log_inventory_change(
        cls,
        db_session,
        product_id: int,
        user_id: int,
        quantity_change: float,
        reference_type: str,
        reference_id: int = None,
        notes: str = None,
        unit_cost: Decimal = None  # new parameter
    ) -> 'InventoryLog':
        """
        Helper method to create an inventory log entry.
        
        Args:
            db_session: Database session
            product_id: ID of the product being updated
            user_id: ID of the user making the change
            quantity_change: Amount to change (positive for addition, negative for reduction)
            reference_type: Type of reference (e.g., 'order', 'return')
            reference_id: Optional ID of the reference document
            notes: Optional notes about the change
            unit_cost: Optional cost per unit at the time of movement
            
        Returns:
            The created InventoryLog instance
        """
        from app.models import Product
        
        # Get the current quantity with row-level locking
        product = db_session.query(Product).with_for_update().get(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")
        
        # Calculate new quantity using Decimal for numeric stability.
        old_quantity = Decimal(str(product.quantity_available if product.quantity_available is not None else 0))
        delta = Decimal(str(quantity_change))
        new_quantity = old_quantity + delta
        
        # Create the log entry
        log = cls(
            product_id=product_id,
            user_id=user_id,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_change=quantity_change,
            quantity_before=float(old_quantity),
            quantity_after=float(new_quantity),
            unit_cost=unit_cost,  # store unit cost if provided
            notes=notes
        )
        
        # Update the product quantity
        product.quantity_available = float(new_quantity)
        
        # Save changes
        db_session.add(log)
        db_session.add(product)
        
        return log

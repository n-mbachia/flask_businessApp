# app/models/inventory_lots.py

from . import db, BaseModelMixin
from sqlalchemy import Index, event
from datetime import datetime
from sqlalchemy.orm import validates, relationship
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .order_item import OrderItem

class InventoryLot(db.Model, BaseModelMixin):
    """
    Represents a record of inventory received for a product.

    Attributes:
        id (int): Primary key of the inventory lot.
        product_id (int): Foreign key referencing the product associated with the inventory lot.
        user_id (int): Foreign key referencing the user associated with the inventory lot.
        lot_number (str): Unique identifier of the inventory lot.
        received_date (datetime.date): Date when the inventory was received.
        quantity_received (int): Number of items received.
        cost_per_unit (float): Cost of each item received.
        expiration_date (datetime.date): Expiration date of the items, if applicable.
        created_at (datetime.datetime): Timestamp when the inventory lot was created.
        updated_at (datetime.datetime): Timestamp when the inventory lot was last updated.

    Relationships:
        product (relationship): Relationship to the product associated with the inventory lot.
        user (relationship): Relationship to the user associated with the inventory lot.
        order_items (relationship): Relationship to the order items associated with the inventory lot.
    """

    __tablename__ = 'inventory_lot'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    lot_number = db.Column(db.String(50), nullable=False, unique=True)
    received_date = db.Column(db.Date, nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False)
    cost_per_unit = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', back_populates='lots')
    user = db.relationship('User', back_populates='inventory_lots')
    order_items = db.relationship('order_item.OrderItem', back_populates='lot')

    __table_args__ = (
        Index('ix_inventory_product_received', 'product_id', 'received_date'),
        Index('ix_inventory_lot_lot_number', 'lot_number'),
    )

    @validates('quantity_received')
    def validate_quantity_received(self, key, value):
        """Ensure quantity received is positive"""
        if value <= 0:
            raise ValueError("Quantity received must be positive")
        return value

    @validates('cost_per_unit')
    def validate_cost_per_unit(self, key, value):
        """Ensure cost per unit is positive"""
        if value <= 0:
            raise ValueError("Cost per unit must be positive")
        return value

    def create_inventory_movement(self):
        """Create an inventory movement record for this lot"""
        from app.models.inventory_movement import InventoryMovement
        
        movement = InventoryMovement(
            product_id=self.product_id,
            movement_type='receipt',
            quantity=self.quantity_received,
            reference_id=self.id,
            reference_type='inventory_lot',
            notes=f'Lot #{self.lot_number} received on {self.received_date}'
        )
        db.session.add(movement)
        return movement

    def update_inventory_movement(self):
        """Update the associated inventory movement when lot is updated"""
        from app.models.inventory_movement import InventoryMovement
        
        movement = InventoryMovement.query.filter_by(
            reference_id=self.id,
            reference_type='inventory_lot'
        ).first()
        
        if movement:
            movement.quantity = self.quantity_received
            movement.notes = f'Updated lot #{self.lot_number} on {datetime.utcnow().date()}'

    def __repr__(self) -> str:
        """Return a string representation of the instance."""
        return f"<InventoryLot lot_number={self.lot_number!r}>"

# Event listeners
@event.listens_for(InventoryLot, 'after_insert')
def after_inventory_lot_insert(mapper, connection, target):
    """Create inventory movement after a new lot is inserted"""
    target.create_inventory_movement()

@event.listens_for(InventoryLot, 'after_update')
def after_inventory_lot_update(mapper, connection, target):
    """Update inventory movement when a lot is updated"""
    target.update_inventory_movement()

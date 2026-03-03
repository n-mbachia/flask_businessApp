# app/models/inventory_movement.py

from app import db
from datetime import datetime
from sqlalchemy import Enum
from sqlalchemy.orm import validates

class InventoryMovement(db.Model):
    """Tracks all inventory movements for products.
    
    Attributes:
        id (int): Primary key
        product_id (int): Foreign key to the product
        movement_type (str): Type of movement (receipt, sale, adjustment_in, adjustment_out, return, damage)
        quantity (int): Quantity moved (positive for additions, negative for deductions)
        unit_cost (Decimal): Cost per unit at time of movement
        total_cost (Decimal): Total cost of movement (quantity * unit_cost)
        reference_id (int): ID of related record (sale, purchase, etc.)
        reference_type (str): Type of reference
        notes (str): Additional notes about the movement
        created_at (datetime): When the movement was created
        updated_at (datetime): When the movement was last updated
    """
    __tablename__ = 'inventory_movements'
    
    # Movement types
    MOVEMENT_TYPES = ('receipt', 'sale', 'adjustment_in', 'adjustment_out', 'return', 'damage')
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.Enum(*MOVEMENT_TYPES, name='movement_types'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=True)  # Cost per unit at time of movement
    total_cost = db.Column(db.Numeric(12, 2), nullable=True)  # quantity * unit_cost
    reference_id = db.Column(db.Integer, nullable=True)  # ID of related record
    reference_type = db.Column(db.String(50), nullable=True)  # 'sale', 'purchase', 'adjustment'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - using string-based foreign_keys
    product = db.relationship(
        'Product',
        back_populates='inventory_movements',
        foreign_keys='InventoryMovement.product_id'  # Using string for foreign key
    )

    def __init__(self, **kwargs):
        super(InventoryMovement, self).__init__(**kwargs)
        # Calculate total cost if unit_cost is provided
        if self.unit_cost is not None and self.quantity is not None:
            self.total_cost = abs(self.quantity) * self.unit_cost
        # Ensure quantity is stored as positive for receipts, negative for deductions
        if self.movement_type in ['sale', 'adjustment_out', 'damage'] and self.quantity > 0:
            self.quantity = -self.quantity

    def __repr__(self):
        return f'<InventoryMovement {self.movement_type} {self.quantity} for product {self.product_id}>'
    
    @validates('movement_type')
    def validate_movement_type(self, key, movement_type):
        """Validate that movement_type is one of the allowed types."""
        if movement_type not in self.MOVEMENT_TYPES:
            raise ValueError(f"Invalid movement type. Must be one of: {', '.join(self.MOVEMENT_TYPES)}")
        return movement_type
    
    @validates('quantity')
    def validate_quantity(self, key, quantity):
        """Validate that quantity is not zero."""
        if quantity == 0:
            raise ValueError("Quantity cannot be zero")
        return quantity
    
    @property
    def is_incoming(self):
        """Check if this is an incoming inventory movement."""
        return self.quantity > 0
    
    @property
    def absolute_quantity(self):
        """Get the absolute value of quantity."""
        return abs(self.quantity)
    
    @property
    def movement_description(self):
        """Get a human-readable description of the movement."""
        descriptions = {
            'receipt': 'Stock Received',
            'sale': 'Sale',
            'adjustment_in': 'Stock Adjustment (In)',
            'adjustment_out': 'Stock Adjustment (Out)',
            'return': 'Customer Return',
            'damage': 'Damaged Stock'
        }
        return descriptions.get(self.movement_type, 'Unknown Movement')

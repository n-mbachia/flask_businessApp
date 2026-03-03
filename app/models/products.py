# app/models/products.py

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from datetime import datetime
from decimal import Decimal
from flask import current_app, url_for
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Index, func, select, and_

from app import db
from app.models import BaseModelMixin

if TYPE_CHECKING:
    from .users import User
    from .sales import Sales
    from .inventory_lots import InventoryLot
    from .inventory_movement import InventoryMovement
    from .costs import CostEntry
    from .order_items import OrderItem
    from .inventory_log import InventoryLog

class Product(db.Model, BaseModelMixin):
    """Represents a product with pricing and margin details.
    
    Attributes:
        id: Primary key of the product
        user_id: Foreign key referencing the user associated with the product
        name: Name of the product
        category: Category of the product
        cogs_per_unit: Cost of goods sold per unit
        selling_price_per_unit: Selling price per unit
        margin_threshold: Custom margin threshold
        reorder_level: Reorder level for the product
        quantity_available: Quantity available of the product
        created_at: Timestamp when the product was created
        updated_at: Timestamp when the product was last updated
    """
    __tablename__ = 'products'
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    category: Mapped[str] = mapped_column(db.String(50), default='Uncategorized', nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(db.Text)
    sku: Mapped[Optional[str]] = mapped_column(db.String(50), unique=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(db.String(50), unique=True, index=True)
    image_filename: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True, index=True)
    cogs_per_unit: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    selling_price_per_unit: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    track_inventory: Mapped[bool] = mapped_column(db.Boolean, default=True)
    margin_threshold: Mapped[Optional[float]] = mapped_column(db.Float)
    reorder_level: Mapped[int] = mapped_column(db.Integer, default=10)
    quantity_available: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, index=True)
    is_approved: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped['User'] = relationship('User', back_populates='products')
    sales: Mapped[List['Sales']] = relationship('Sales', back_populates='product', cascade='all, delete-orphan')
    lots: Mapped[List['InventoryLot']] = relationship('InventoryLot', back_populates='product', cascade='all, delete-orphan')
    inventory_movements: Mapped[List['InventoryMovement']] = relationship(
        'InventoryMovement', 
        back_populates='product', 
        cascade='all, delete-orphan'
    )
    inventory_logs: Mapped[List['InventoryLog']] = relationship(
        'InventoryLog',
        back_populates='product',
        cascade='all, delete-orphan',
        order_by='desc(InventoryLog.created_at)'
    )
    cost_entries: Mapped[List['CostEntry']] = relationship('CostEntry', back_populates='product', cascade='all, delete-orphan')
    order_items: Mapped[List['OrderItem']] = relationship('OrderItem', back_populates='product', cascade='all, delete-orphan')
     
    # Indexes
    __table_args__ = (
        Index('idx_product_user_name', 'user_id', 'name', unique=True),
        Index('idx_product_user_sku', 'user_id', 'sku', unique=True, postgresql_where=sku.isnot(None)),
        Index('idx_product_user_barcode', 'user_id', 'barcode', unique=True, postgresql_where=barcode.isnot(None)),
    )
    
    @hybrid_property
    def current_stock(self) -> int:
        """Calculate current stock level by summing all inventory movements."""
        from .inventory_movement import InventoryMovement
        
        total = db.session.query(
            func.coalesce(func.sum(InventoryMovement.quantity), 0)
        ).filter(
            InventoryMovement.product_id == self.id
        ).scalar()
        
        return int(total) if total is not None else 0
    
    @property
    def stock_quantity(self) -> int:
        """API‑friendly alias for current stock (used by Flask‑RESTx marshalling)."""
        return self.current_stock

    @hybrid_property
    def price(self) -> Decimal:
        """Convenience alias for selling price."""
        return self.selling_price_per_unit

    @property
    def image_url(self) -> str:
        """Return the full URL for the product image, falling back to the default."""
        filename = self.image_filename or current_app.config.get('DEFAULT_PRODUCT_IMAGE', 'images/default-product.png')
        try:
            return url_for('static', filename=filename)
        except RuntimeError:
            return filename

    def __init__(self, **kwargs):
        price = kwargs.pop('price', None)
        current_stock = kwargs.pop('current_stock', None)
        track_inventory = kwargs.pop('track_inventory', None)
        super().__init__(**kwargs)

        if price is not None and not self.selling_price_per_unit:
            self.selling_price_per_unit = Decimal(str(price))

        if self.selling_price_per_unit is None:
            self.selling_price_per_unit = Decimal('0.00')

        if self.cogs_per_unit is None:
            self.cogs_per_unit = Decimal('0.00')

        if current_stock is not None and (self.quantity_available is None):
            self.quantity_available = float(current_stock)

        if track_inventory is not None:
            self.track_inventory = bool(track_inventory)
    
    @current_stock.expression
    def current_stock(cls):
        """SQL expression for current stock calculation."""
        from .inventory_movement import InventoryMovement
        
        return select(
            func.coalesce(func.sum(InventoryMovement.quantity), 0)
        ).where(
            InventoryMovement.product_id == cls.id
        ).label('current_stock')
    
    @hybrid_property
    def total_value(self) -> Decimal:
        """Calculate total inventory value."""
        return self.cogs_per_unit * Decimal(str(self.current_stock))
    
    @hybrid_property
    def margin_percentage(self) -> float:
        """Calculate the profit margin percentage for the product."""
        if not self.selling_price_per_unit:
            return 0.0
        return float(
            ((self.selling_price_per_unit - self.cogs_per_unit) / self.selling_price_per_unit) * 100
        )
    
    @hybrid_property
    def effective_margin_threshold(self) -> float:
        """Get the effective margin threshold, falling back to user's default if not set."""
        return float(self.margin_threshold) if self.margin_threshold is not None else float(self.user.threshold)
    
    @effective_margin_threshold.expression
    def effective_margin_threshold(cls):
        """SQL expression for effective margin threshold calculation."""
        from app.models.users import User
        return db.case(
            (cls.margin_threshold.isnot(None), cls.margin_threshold),
            else_=User.threshold
        )
    
    @hybrid_property
    def is_below_reorder_level(self) -> bool:
        """Check if current stock is below reorder level."""
        return self.current_stock <= self.reorder_level
    
    @hybrid_property
    def is_below_margin_threshold(self) -> bool:
        """Check if current margin is below threshold."""
        if self.margin_threshold is None:
            return False
        return self.margin_percentage < self.margin_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'image_url': self.image_url,
            'image_filename': self.image_filename,
            'sku': self.sku,
            'barcode': self.barcode,
            'cogs_per_unit': float(self.cogs_per_unit),
            'selling_price_per_unit': float(self.selling_price_per_unit),
            'margin_threshold': self.margin_threshold,
            'reorder_level': self.reorder_level,
            'current_stock': self.current_stock,
            'total_value': float(self.total_value) if self.total_value else 0.0,
            'margin_percentage': self.margin_percentage,
            'is_below_reorder_level': self.is_below_reorder_level,
            'is_below_margin_threshold': self.is_below_margin_threshold,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f'<Product {self.name} (ID: {self.id})>'

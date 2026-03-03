from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app
from sqlalchemy.orm import Mapped, mapped_column, relationship
from itsdangerous import SignatureExpired, BadSignature, URLSafeTimedSerializer as Serializer

from app import db
from app.models.base import BaseModelMixin

# Use string-based forward references to avoid circular imports
if TYPE_CHECKING:
    from .products import Product
    from .sales import Sales
    from .inventory_lots import InventoryLot
    from .costs import CostEntry
    from .orders import Order
    from .customers import Customer
    from .inventory_log import InventoryLog

class User(UserMixin, db.Model, BaseModelMixin):
    """
    User model for authentication and user management.
    """
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(db.String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(256), nullable=False)
    confirmed: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    confirmed_on: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    threshold: Mapped[float] = mapped_column(db.Float, default=10.0)
    last_login: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    email_notifications: Mapped[bool] = mapped_column(db.Boolean, default=True)
    low_stock_alerts: Mapped[bool] = mapped_column(db.Boolean, default=True)
    items_per_page: Mapped[int] = mapped_column(db.Integer, default=10)
    theme: Mapped[str] = mapped_column(db.String(20), default='light')
    currency: Mapped[str] = mapped_column(db.String(3), default='USD')
    is_vendor: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)
    is_admin: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # Relationships
    products: Mapped[List['Product']] = relationship('Product', back_populates='user', cascade='all, delete-orphan')
    sales: Mapped[List['Sales']] = relationship('Sales', back_populates='user', cascade='all, delete-orphan')
    inventory_lots: Mapped[List['InventoryLot']] = relationship('InventoryLot', back_populates='user', cascade='all, delete-orphan')
    inventory_logs: Mapped[List['InventoryLog']] = relationship(
        'InventoryLog', 
        back_populates='user', 
        cascade='all, delete-orphan',
        order_by='desc(InventoryLog.created_at)'
    )
    cost_entries: Mapped[List['CostEntry']] = relationship('CostEntry', back_populates='user', cascade='all, delete-orphan')
    orders: Mapped[List['Order']] = relationship('Order', back_populates='user', cascade='all, delete-orphan')
    customers: Mapped[List['Customer']] = relationship('Customer', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if 'password' in kwargs:
            self.set_password(kwargs['password'])
        if not getattr(self, 'password_hash', None):
            # Ensure a non-null password hash for tests and fixtures
            self.password_hash = generate_password_hash('test-password')
    
    def set_password(self, password: str) -> None:
        """Set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def generate_confirmation_token(self) -> str:
        """Generate a confirmation token for email verification."""
        salt = current_app.config.get('EMAIL_CONFIRMATION_SALT', 'businessapp-email-confirm')
        serializer = Serializer(current_app.config['SECRET_KEY'], salt)
        return serializer.dumps({'confirm': self.id})
    
    def confirm(self, token: str) -> bool:
        """Verify the confirmation token and confirm the user's email."""
        salt = current_app.config.get('EMAIL_CONFIRMATION_SALT', 'businessapp-email-confirm')
        serializer = Serializer(current_app.config['SECRET_KEY'], salt)
        max_age = current_app.config.get('EMAIL_CONFIRMATION_EXPIRATION', 3600)
        try:
            data = serializer.loads(token, max_age=max_age)
        except (SignatureExpired, BadSignature):
            return False
        except Exception:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        self.confirmed_on = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
        return True
    
    def __repr__(self) -> str:
        return f'<User {self.username}>'

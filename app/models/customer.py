# app/models/customer.py

from __future__ import annotations
from datetime import datetime
import re
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import validates, Mapped, mapped_column, relationship

from app import db
from app.models.base import BaseModelMixin

if TYPE_CHECKING:
    from .orders import Order
    from .users import User

class Customer(db.Model, BaseModelMixin):
    """
    Represents a customer in the system.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to the user who owns this customer
        user (User): Relationship to the User model
        name (str): Full name of the customer
        email (str): Email address (must be unique)
        phone (str): Contact number
        company (str, optional): Company name
        address (str): Street address
        city (str): City
        state (str): State/Province
        postal_code (str): Postal/ZIP code
        country (str): Country
        tax_id (str, optional): Tax/VAT identification number
        is_active (bool): Whether the customer is active
        notes (str, optional): Additional notes
        created_at (datetime): When the customer was created
        updated_at (datetime): When the customer was last updated
    """
    __tablename__ = 'customers'
    
    # Email validation regex
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE_REGEX = r'^[\d\s\-+\(\)]{6,20}$'  # Basic phone number validation

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(db.String(120), unique=True)
    phone: Mapped[Optional[str]] = mapped_column(db.String(20))
    company: Mapped[Optional[str]] = mapped_column(db.String(120))
    address: Mapped[Optional[str]] = mapped_column(db.String(255))
    address2: Mapped[Optional[str]] = mapped_column(db.String(255))
    city: Mapped[Optional[str]] = mapped_column(db.String(100))
    state: Mapped[Optional[str]] = mapped_column(db.String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(db.String(20))
    country: Mapped[Optional[str]] = mapped_column(db.String(100), default='United States')
    tax_id: Mapped[Optional[str]] = mapped_column(db.String(50))
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(db.Text)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped['User'] = relationship('User', back_populates='customers')
    orders: Mapped[List['Order']] = relationship('Order', back_populates='customer', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        # Normalize email to lowercase
        if 'email' in kwargs and kwargs['email']:
            kwargs['email'] = kwargs['email'].lower().strip()
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Customer {self.id}: {self.name}>"
    
    @validates('email')
    def validate_email(self, key, email):
        if email:
            email = email.lower().strip()
            if not re.match(self.EMAIL_REGEX, email, re.IGNORECASE):
                raise ValueError("Invalid email format")
        return email
    
    @validates('phone')
    def validate_phone(self, key, phone):
        if phone:
            phone = phone.strip()
            if not re.match(self.PHONE_REGEX, phone):
                raise ValueError("Invalid phone number format. Use format: +1 (123) 456-7890")
        return phone
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return name.strip()
    
    def get_full_address(self):
        """Return formatted address as a single string."""
        parts = [self.address]
        if self.address2:
            parts.append(self.address2)
        if self.city:
            parts.append(self.city)
        if self.state or self.postal_code:
            state_zip = ' '.join(filter(None, [self.state, self.postal_code]))
            parts.append(state_zip)
        if self.country:
            parts.append(self.country)
        return ', '.join(parts) if any(parts) else None
    
    def get_order_count(self):
        """Return the total number of orders for this customer."""
        return len(self.orders)
    
    def get_total_spent(self):
        """Return the total amount spent by this customer."""
        from app.models.orders import Order
        return sum(
            float(order.total_amount) for order in self.orders
            if order.status == Order.STATUS_COMPLETED
        )
    
    def to_dict(self):
        """Convert customer to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'address': self.address,
            'address2': self.address2,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'tax_id': self.tax_id,
            'is_active': self.is_active,
            'notes': self.notes,
            'order_count': self.get_order_count(),
            'total_spent': str(self.get_total_spent()),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def search(cls, query):
        """Search customers by name, email, or company."""
        search_term = f"%{query}%"
        return cls.query.filter(
            (cls.name.ilike(search_term)) | 
            (cls.email.ilike(search_term)) | 
            (cls.company.ilike(search_term))
        ).all()

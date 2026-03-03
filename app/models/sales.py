# app/models/sales.py

from app.models import db, BaseModelMixin
from sqlalchemy import Index
from datetime import datetime

class Sales(db.Model, BaseModelMixin):
    """
    Monthly aggregated sales snapshot.
    Populated automatically from Orders.

    Attributes:
        id (int): Primary key.
        product_id (int): Foreign key referencing the product.
        month (str): The month to which the sale pertains, formatted as YYYY-MM.
        units_sold (int): Total number of units sold for the product in that month.
        total_revenue (float): Total revenue generated from the product in that month.
        customer_count (int): Number of unique customers who bought this product in that month.
        user_id (int): Foreign key referencing the user (owner of the data).
        created_at (datetime): When the record was created.
        updated_at (datetime): When the record was last updated.
    """
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    units_sold = db.Column(db.Integer, nullable=False, default=0)
    total_revenue = db.Column(db.Numeric(12, 2), default=0.0)
    customer_count = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship("Product", back_populates="sales")
    user = db.relationship("User", back_populates="sales")

    __table_args__ = (
        Index('ix_sales_product_month', 'product_id', 'month'),
        Index('ix_sales_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Sales {self.product_id} - {self.month}>"

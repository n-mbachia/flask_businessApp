"""
Models package initialization.
This file ensures all models are properly registered with SQLAlchemy.
"""
# Import the db instance from the app package to avoid circular imports
from app import db
from sqlalchemy import inspect, text
from .base import BaseModelMixin

# Import all models here to ensure they are registered with SQLAlchemy
# The order of imports matters to avoid circular imports
from .users import User
from .products import Product
from .customer import Customer
from .orders import Order
from .order_item import OrderItem
from .inventory_lots import InventoryLot
from .inventory_movement import InventoryMovement
from .inventory_log import InventoryLog
from .costs import CostEntry, CostType, CostTypeEnum
Costs = CostEntry
from .sales import Sales
from .analytics_views import create_analytics_views, drop_analytics_views

def init_db(app):
    """Initialize the database with the given Flask app."""
    # Don't initialize db here as it's already initialized in app/__init__.py
    with app.app_context():
        try:
            # Create all database tables
            db.create_all()

            # Ensure required columns exist for legacy SQLite databases.
            _ensure_users_columns(app)
            _ensure_orders_columns(app)
            _ensure_products_columns(app)
            
            # Create analytics views
            create_analytics_views()
            
            # Create default cost types if they don't exist
            create_default_cost_types()
            
            db.session.commit()
            app.logger.info("Database tables and views created successfully.")
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error initializing database: {str(e)}")
            raise

def _ensure_orders_columns(app):
    """Add missing columns to orders table for legacy SQLite databases."""
    try:
        if db.engine.dialect.name != 'sqlite':
            return

        inspector = inspect(db.engine)
        if 'orders' not in inspector.get_table_names():
            return

        existing = {col['name'] for col in inspector.get_columns('orders')}
        required = {
            'subtotal': "ALTER TABLE orders ADD COLUMN subtotal NUMERIC(10,2) NOT NULL DEFAULT 0.00",
            'tax_amount': "ALTER TABLE orders ADD COLUMN tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00",
            'shipping_amount': "ALTER TABLE orders ADD COLUMN shipping_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00",
            'discount_amount': "ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00",
            'source': "ALTER TABLE orders ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'manual'"
        }

        with db.engine.begin() as conn:
            for column, ddl in required.items():
                if column not in existing:
                    conn.execute(text(ddl))
                    app.logger.info("Added missing orders.%s column", column)
    except Exception as exc:
        app.logger.error("Failed to ensure orders columns: %s", exc)


def _ensure_users_columns(app):
    """Add missing columns to users table for legacy SQLite databases."""
    try:
        if db.engine.dialect.name != 'sqlite':
            return

        inspector = inspect(db.engine)
        if 'users' not in inspector.get_table_names():
            return

        existing = {col['name'] for col in inspector.get_columns('users')}
        required = {
            'is_vendor': "ALTER TABLE users ADD COLUMN is_vendor BOOLEAN NOT NULL DEFAULT 0",
            'is_admin': "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0",
        }

        with db.engine.begin() as conn:
            for column, ddl in required.items():
                if column not in existing:
                    conn.execute(text(ddl))
                    app.logger.info("Added missing users.%s column", column)
    except Exception as exc:
        app.logger.error("Failed to ensure users columns: %s", exc)


def _ensure_products_columns(app):
    """Add missing columns to products table for legacy SQLite databases."""
    try:
        if db.engine.dialect.name != 'sqlite':
            return

        inspector = inspect(db.engine)
        if 'products' not in inspector.get_table_names():
            return

        existing = {col['name'] for col in inspector.get_columns('products')}
        required = {
            'track_inventory': "ALTER TABLE products ADD COLUMN track_inventory BOOLEAN NOT NULL DEFAULT 1",
            'margin_threshold': "ALTER TABLE products ADD COLUMN margin_threshold FLOAT",
            'is_approved': "ALTER TABLE products ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 0",
            'image_filename': "ALTER TABLE products ADD COLUMN image_filename VARCHAR(255)"
        }

        with db.engine.begin() as conn:
            for column, ddl in required.items():
                if column not in existing:
                    conn.execute(text(ddl))
                    app.logger.info("Added missing products.%s column", column)
    except Exception as exc:
        app.logger.error("Failed to ensure products columns: %s", exc)

def create_default_cost_types():
    """Create default cost types if they don't exist."""
    from .costs import CostType
    
    default_cost_types = [
        ('raw_materials', 'Raw Materials'),
        ('labor', 'Labor'),
        ('shipping', 'Shipping'),
        ('packaging', 'Packaging'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('marketing', 'Marketing'),
        ('other', 'Other')
    ]
    
    for type_id, name in default_cost_types:
        cost_type = CostType.query.filter_by(id=type_id).first()
        if not cost_type:
            cost_type = CostType(id=type_id, name=name)
            db.session.add(cost_type)
    
    db.session.commit()

# Set up event listeners for model relationships
def setup_event_listeners():
    """Set up SQLAlchemy event listeners."""
    from sqlalchemy.orm import backref, relationship
    
    # Set up relationships that couldn't be defined in the model files
    # due to circular imports
    if not hasattr(Order, 'items'):
        Order.items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    if not hasattr(OrderItem, 'order'):
        OrderItem.order = relationship("Order", back_populates="items")
    
    if not hasattr(OrderItem, 'product'):
        OrderItem.product = relationship("Product", back_populates="order_items")
    
    if not hasattr(Product, 'order_items'):
        Product.order_items = relationship("OrderItem", back_populates="product")
    
    if not hasattr(Order, 'customer'):
        Order.customer = relationship("Customer", back_populates="orders")
    
    if not hasattr(Customer, 'orders'):
        Customer.orders = relationship("Order", back_populates="customer")
    
    if not hasattr(Order, 'user'):
        Order.user = relationship("User", back_populates="orders")
    
    if not hasattr(User, 'orders'):
        User.orders = relationship("Order", back_populates="user")

# Call the setup function when the models are loaded
setup_event_listeners()

# Create a dictionary of model names to model classes for easy access
__all__ = [
    'db',
    'BaseModelMixin',
    'User',
    'Customer',
    'Product',
    'ProductCategory',
    'ProductVariant',
    'Order',
    'OrderItem',
    'Invoice',
    'InvoiceItem',
    'Payment',
    'Setting',
    'InventoryLog',
    'InventoryLot',
    'InventoryMovement',
    'CostEntry',
    'Costs',
    'CostType',
    'CostTypeEnum',
    'Sales',
    'create_analytics_views',
    'drop_analytics_views',
    'init_db'
]

"""
Database views for analytics to improve query performance.
These views materialize commonly used aggregations.
"""
import logging
from sqlalchemy import text, inspect
from app import db

logger = logging.getLogger(__name__)

def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check whether the given table exposes the requested column."""
    return column_name in {col['name'] for col in inspector.get_columns(table_name)}

def create_analytics_views():
    """
    Create or replace database views for analytics.
    This function should be called during application startup.
    """
    inspector = inspect(db.engine)

    if not _has_column(inspector, 'orders', 'source'):
        logger.warning("Skipping analytics view creation because orders.source column is missing.")
        return
    
    # Monthly Sales View
    if 'monthly_sales_view' in inspector.get_view_names():
        db.session.execute(text('DROP VIEW monthly_sales_view'))
        db.session.commit()
    
    # Create the view using the dialect that fits the current database.
    dialect_name = db.engine.dialect.name
    is_sqlite = dialect_name == 'sqlite'

    if is_sqlite:
        monthly_view_sql = """
        CREATE VIEW monthly_sales_view AS
        SELECT 
            o.user_id,
            COALESCE(o.source, 'manual') AS order_source,
            strftime('%Y', o.order_date) AS year,
            strftime('%m', o.order_date) AS month,
            oi.product_id,
            p.name AS product_name,
            p.category AS product_category,
            SUM(oi.quantity) AS total_quantity,
            SUM(oi.subtotal) AS total_revenue,
            COUNT(DISTINCT o.customer_id) AS customer_count,
            COUNT(DISTINCT o.id) AS order_count
        FROM 
            orders o
        JOIN 
            order_items oi ON o.id = oi.order_id
        JOIN 
            products p ON oi.product_id = p.id
        WHERE 
            o.status = 'completed'
        GROUP BY 
            o.user_id, 
            COALESCE(o.source, 'manual'),
            strftime('%Y', o.order_date),
            strftime('%m', o.order_date),
            oi.product_id,
            p.name,
            p.category;
        """
    else:
        monthly_view_sql = """
        CREATE OR REPLACE VIEW monthly_sales_view AS
        SELECT 
            o.user_id,
            COALESCE(o.source, 'manual') AS order_source,
            EXTRACT(YEAR FROM o.order_date)::text AS year,
            LPAD(EXTRACT(MONTH FROM o.order_date)::text, 2, '0') AS month,
            oi.product_id,
            p.name AS product_name,
            p.category AS product_category,
            SUM(oi.quantity) AS total_quantity,
            SUM(oi.subtotal) AS total_revenue,
            COUNT(DISTINCT o.customer_id) AS customer_count,
            COUNT(DISTINCT o.id) AS order_count
        FROM 
            orders o
        JOIN 
            order_items oi ON o.id = oi.order_id
        JOIN 
            products p ON oi.product_id = p.id
        WHERE 
            o.status = 'completed'
        GROUP BY 
            o.user_id, 
            COALESCE(o.source, 'manual'),
            EXTRACT(YEAR FROM o.order_date),
            EXTRACT(MONTH FROM o.order_date),
            oi.product_id,
            p.name,
            p.category;
        """

    db.session.execute(text(monthly_view_sql))
    db.session.commit()

    # Product Sales View
    if 'product_sales_view' in inspector.get_view_names():
        db.session.execute(text('DROP VIEW IF EXISTS product_sales_view'))
        db.session.commit()
    
    db.session.execute(text("""
    CREATE VIEW product_sales_view AS
    SELECT 
        o.user_id,
        COALESCE(o.source, 'manual') AS order_source,
        oi.product_id,
        p.name AS product_name,
        p.category AS product_category,
        p.cogs_per_unit,
        p.selling_price_per_unit,
        SUM(oi.quantity) AS total_units_sold,
        SUM(oi.subtotal) AS total_revenue,
        SUM(oi.quantity * p.cogs_per_unit) AS total_cogs,
        SUM(oi.subtotal - (oi.quantity * p.cogs_per_unit)) AS total_profit,
        COUNT(DISTINCT o.customer_id) AS customer_count,
        COUNT(DISTINCT o.id) AS order_count
    FROM 
        orders o
    JOIN 
        order_items oi ON o.id = oi.order_id
    JOIN 
        products p ON oi.product_id = p.id
    WHERE 
        o.status = 'completed'
    GROUP BY 
        o.user_id, 
        COALESCE(o.source, 'manual'),
        oi.product_id,
        p.name,
        p.category,
        p.cogs_per_unit,
        p.selling_price_per_unit
    
    """))
    db.session.commit()

    # Customer Sales View
    if 'customer_sales_view' in inspector.get_view_names():
        db.session.execute(text('DROP VIEW customer_sales_view'))
        db.session.commit()
    
    db.session.execute(text("""
    CREATE VIEW customer_sales_view AS
    SELECT 
        o.user_id,
        COALESCE(o.source, 'manual') AS order_source,
        o.customer_id,
        c.name AS customer_name,
        c.email AS customer_email,
        COUNT(DISTINCT o.id) AS order_count,
        COUNT(DISTINCT oi.product_id) AS unique_products_purchased,
        SUM(oi.quantity) AS total_units_purchased,
        SUM(oi.subtotal) AS total_spent,
        MIN(o.order_date) AS first_purchase_date,
        MAX(o.order_date) AS last_purchase_date
    FROM 
        orders o
    JOIN 
        order_items oi ON o.id = oi.order_id
    JOIN 
        customers c ON o.customer_id = c.id
    WHERE 
        o.status = 'completed'
    GROUP BY 
        o.user_id, 
        COALESCE(o.source, 'manual'),
        o.customer_id,
        c.name,
        c.email;
    
    """))
    db.session.commit()

    # Daily Sales View
    if 'daily_sales_view' in inspector.get_view_names():
        db.session.execute(text('DROP VIEW daily_sales_view'))
        db.session.commit()
    
    db.session.execute(text("""
    CREATE VIEW daily_sales_view AS
    SELECT 
        o.user_id,
        DATE(o.order_date) AS sale_date,
        COALESCE(o.source, 'manual') AS order_source,
        COUNT(DISTINCT o.id) AS order_count,
        COUNT(DISTINCT o.customer_id) AS customer_count,
        COUNT(DISTINCT oi.product_id) AS unique_products_sold,
        SUM(oi.quantity) AS total_units_sold,
        SUM(oi.subtotal) AS total_revenue,
        AVG(oi.subtotal) AS avg_order_value
    FROM 
        orders o
    JOIN 
        order_items oi ON o.id = oi.order_id
    WHERE 
        o.status = 'completed'
    GROUP BY 
        o.user_id, 
        DATE(o.order_date),
        COALESCE(o.source, 'manual');
    
    """))
    db.session.commit()

    # Category Sales View
    if 'category_sales_view' in inspector.get_view_names():
        db.session.execute(text('DROP VIEW category_sales_view'))
        db.session.commit()
    
    db.session.execute(text("""
    CREATE VIEW category_sales_view AS
    SELECT 
        o.user_id,
        COALESCE(o.source, 'manual') AS order_source,
        p.category,
        COUNT(DISTINCT o.id) AS order_count,
        COUNT(DISTINCT o.customer_id) AS customer_count,
        COUNT(DISTINCT oi.product_id) AS unique_products_sold,
        SUM(oi.quantity) AS total_units_sold,
        SUM(oi.subtotal) AS total_revenue,
        SUM(oi.quantity * p.cogs_per_unit) AS total_cogs,
        SUM(oi.subtotal - (oi.quantity * p.cogs_per_unit)) AS total_profit,
        AVG(oi.subtotal) AS avg_order_value
    FROM 
        orders o
    JOIN 
        order_items oi ON o.id = oi.order_id
    JOIN 
        products p ON oi.product_id = p.id
    WHERE 
        o.status = 'completed'
        AND p.category IS NOT NULL
    GROUP BY 
        o.user_id, 
        COALESCE(o.source, 'manual'),
        p.category;
    
    """))
    db.session.commit()


def drop_analytics_views():
    """
    Drop all analytics views.
    This function can be used for cleanup or testing.
    """
    inspector = inspect(db.engine)
    
    views_to_drop = [
        'monthly_sales_view',
        'product_sales_view',
        'customer_sales_view',
        'daily_sales_view',
        'category_sales_view'
    ]
    
    for view_name in views_to_drop:
        if view_name in inspector.get_view_names():
            db.session.execute(text(f'DROP VIEW {view_name}'))
    
    db.session.commit()

# app/services/sales_updater.py

from datetime import datetime
from app.models import db, Sales, Order, OrderItem

class SalesUpdater:
    """Handles updating aggregated sales data from orders."""

    @staticmethod
    def update_sales_from_order(order: Order):
        """Update Sales aggregates when an order is completed."""
        if order.status != "completed":
            return  # Only completed orders count as sales

        month = order.order_date.strftime("%Y-%m")
        customer_id = order.customer_id

        for item in order.items:
            sales_record = db.session.query(Sales).filter_by(
                product_id=item.product_id,
                user_id=order.user_id,
                month=month
            ).first()

            if not sales_record:
                # Create new record for the month
                sales_record = Sales(
                    product_id=item.product_id,
                    user_id=order.user_id,
                    month=month,
                    units_sold=0,
                    total_revenue=0.0,
                    customer_count=0
                )
                db.session.add(sales_record)

            # Update metrics
            sales_record.units_sold += item.quantity
            sales_record.total_revenue += float(item.subtotal)

            # Increment customer count (unique per month/product)
            already_counted = db.session.query(Sales).filter(
                Sales.product_id == item.product_id,
                Sales.user_id == order.user_id,
                Sales.month == month
            ).filter(
                Sales.customer_count > 0
            ).first()

            if not already_counted:
                sales_record.customer_count += 1

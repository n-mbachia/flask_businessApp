from app import create_app, db
from app.models import Order, Customer, OrderItem

def check_orders():
    app = create_app()
    with app.app_context():
        # Get count of orders by status
        status_counts = db.session.query(
            Order.status,
            db.func.count(Order.id)
        ).group_by(Order.status).all()
        
        print("\nOrder Counts by Status:")
        print("-" * 30)
        for status, count in status_counts:
            print(f"{status}: {count}")
        
        # Get a few sample orders with customer info
        print("\nSample Orders (5 most recent):")
        print("-" * 30)
        orders = Order.query.options(
            db.joinedload(Order.customer),
            db.joinedload(Order.items)
        ).order_by(Order.created_at.desc()).limit(5).all()
        
        for order in orders:
            customer_name = order.customer.name if order.customer else 'No Customer'
            print(f"ID: {order.id}")
            print(f"  Number: {order.order_number}")
            print(f"  Status: {order.status}")
            print(f"  Customer: {customer_name}")
            print(f"  Date: {order.created_at}")
            print(f"  Items: {len(order.items)}")
            print(f"  Total: {order.total_amount}")
            print()

if __name__ == "__main__":
    check_orders()

from app import create_app, db
from app.models import Order

app = create_app()

with app.app_context():
    # Get order counts by status
    status_counts = db.session.query(
        Order.status,
        db.func.count(Order.id)
    ).group_by(Order.status).all()
    
    print("\nOrder counts by status:")
    print("-" * 30)
    for status, count in status_counts:
        print(f"{status}: {count}")
    
    # Get a few sample completed orders
    completed_orders = Order.query.filter_by(status='completed').limit(5).all()
    
    if completed_orders:
        print("\nSample completed orders:")
        print("-" * 30)
        for order in completed_orders:
            print(f"ID: {order.id}, Number: {order.order_number}, Date: {order.order_date}, Total: {order.total_amount}")
    else:
        print("\nNo completed orders found in the database.")

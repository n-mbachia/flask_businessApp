import pytest
from datetime import datetime, timedelta
from app.models import db, User, Product, Order, OrderItem

def test_user_model(db):
    """Test user model."""
    # Create a test user
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash='testpasswordhash',
        first_name='Test',
        last_name='User',
        is_active=True,
        is_admin=False
    )
    db.session.add(user)
    db.session.commit()
    
    # Test user attributes
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.check_password('testpasswordhash')  # Assuming you have a check_password method
    assert user.first_name == 'Test'
    assert user.last_name == 'User'
    assert user.is_active is True
    assert user.is_admin is False
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)
    
    # Test user string representation
    assert str(user) == '<User testuser>'
    assert repr(user) == f'<User {user.id} testuser>'

def test_product_model(db):
    """Test product model."""
    # Create a test product
    product = Product(
        name='Test Product',
        description='Test Description',
        price=19.99,
        stock=100,
        sku='TEST123',
        category='Test Category',
        is_active=True
    )
    db.session.add(product)
    db.session.commit()
    
    # Test product attributes
    assert product.name == 'Test Product'
    assert product.description == 'Test Description'
    assert product.price == 19.99
    assert product.stock == 100
    assert product.sku == 'TEST123'
    assert product.category == 'Test Category'
    assert product.is_active is True
    assert isinstance(product.created_at, datetime)
    assert isinstance(product.updated_at, datetime)
    
    # Test product string representation
    assert str(product) == 'Test Product'
    assert repr(product) == f'<Product {product.id} Test Product>'

def test_order_model(db):
    """Test order model with relationships."""
    # Create a test user
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash='testpasswordhash'
    )
    
    # Create test products
    product1 = Product(
        name='Product 1',
        description='Description 1',
        price=10.00,
        stock=50
    )
    product2 = Product(
        name='Product 2',
        description='Description 2',
        price=20.00,
        stock=30
    )
    
    # Create an order
    order = Order(
        user=user,
        status='pending',
        total_amount=50.00,
        shipping_address='123 Test St, Test City',
        payment_method='credit_card'
    )
    
    # Add order items
    item1 = OrderItem(
        product=product1,
        quantity=2,
        price=10.00
    )
    
    item2 = OrderItem(
        product=product2,
        quantity=3,
        price=20.00
    )
    
    order.items.extend([item1, item2])
    
    db.session.add_all([user, product1, product2, order, item1, item2])
    db.session.commit()
    
    # Test order attributes
    assert order.user_id == user.id
    assert order.status == 'pending'
    assert order.total_amount == 80.00  # 2*10 + 3*20
    assert order.shipping_address == '123 Test St, Test City'
    assert order.payment_method == 'credit_card'
    assert len(order.items) == 2
    assert order.items[0].product_id == product1.id
    assert order.items[1].product_id == product2.id
    
    # Test order string representation
    assert str(order) == f'<Order {order.id}>'
    assert repr(order) == f'<Order {order.id} {order.status} {order.total_amount}>'

def test_order_item_model(db):
    """Test order item model."""
    # Create test user, product, and order
    user = User(username='testuser', email='test@example.com', password_hash='test')
    product = Product(name='Test Product', price=10.00, stock=100)
    order = Order(user=user, status='pending', total_amount=20.00)
    
    # Create order item
    order_item = OrderItem(
        order=order,
        product=product,
        quantity=2,
        price=10.00
    )
    
    db.session.add_all([user, product, order, order_item])
    db.session.commit()
    
    # Test order item attributes
    assert order_item.order_id == order.id
    assert order_item.product_id == product.id
    assert order_item.quantity == 2
    assert order_item.price == 10.00
    assert order_item.subtotal == 20.00  # quantity * price
    
    # Test order item string representation
    assert str(order_item) == f'<OrderItem {order_item.id}>'
    assert repr(order_item) == f'<OrderItem {order_item.id} {order_item.product.name} x{order_item.quantity}>'

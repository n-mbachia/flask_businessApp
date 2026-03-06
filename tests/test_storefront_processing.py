from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models import InventoryMovement, Order, OrderItem, Product, User
from app.services.business_metrics import BusinessMetrics


def test_storefront_checkout_defaults_completed_and_persists_tax(client, db):
    vendor = User(username='vendor1', email='vendor1@example.com')
    db.session.add(vendor)
    db.session.flush()

    product = Product(
        user_id=vendor.id,
        name='Storefront Widget',
        category='Tools',
        cogs_per_unit=Decimal('10.00'),
        selling_price_per_unit=Decimal('25.00'),
        is_active=True,
        is_approved=True
    )
    db.session.add(product)
    db.session.flush()

    db.session.add(InventoryMovement(
        product_id=product.id,
        movement_type='receipt',
        quantity=20,
        unit_cost=Decimal('10.00'),
        notes='seed inventory'
    ))
    db.session.commit()

    response = client.post('/storefront/checkout', json={
        'customer_name': 'Jane Doe',
        'customer': {'name': 'Jane Doe', 'email': 'jane@example.com'},
        'tax_rate': 0.16,
        'items': [{'product_id': product.id, 'quantity': 2}]
    })

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True

    order = Order.query.get(payload['order_id'])
    assert order is not None
    assert order.source == Order.SOURCE_STOREFRONT
    assert order.status == Order.STATUS_COMPLETED
    assert order.payment_status == Order.PAYMENT_PAID
    assert float(order.subtotal) == 50.0
    assert float(order.tax_amount) == 8.0
    assert float(order.total_amount) == 58.0


def test_business_metrics_include_storefront_profitability_breakdown(db):
    user = User(username='metrics_vendor', email='metrics_vendor@example.com')
    db.session.add(user)
    db.session.flush()

    manual_product = Product(
        user_id=user.id,
        name='Manual Product',
        category='General',
        cogs_per_unit=Decimal('40.00'),
        selling_price_per_unit=Decimal('100.00'),
        is_active=True,
        is_approved=True
    )
    storefront_product = Product(
        user_id=user.id,
        name='Store Product',
        category='General',
        cogs_per_unit=Decimal('30.00'),
        selling_price_per_unit=Decimal('100.00'),
        is_active=True,
        is_approved=True
    )
    db.session.add_all([manual_product, storefront_product])
    db.session.flush()

    order_time = datetime.utcnow() - timedelta(days=1)
    manual_order = Order(
        user_id=user.id,
        order_date=order_time,
        status=Order.STATUS_COMPLETED,
        payment_status=Order.PAYMENT_PAID,
        source=Order.SOURCE_MANUAL,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('16.00'),
        total_amount=Decimal('116.00')
    )
    storefront_order = Order(
        user_id=user.id,
        order_date=order_time,
        status=Order.STATUS_COMPLETED,
        payment_status=Order.PAYMENT_PAID,
        source=Order.SOURCE_STOREFRONT,
        subtotal=Decimal('200.00'),
        tax_amount=Decimal('32.00'),
        total_amount=Decimal('232.00')
    )
    db.session.add_all([manual_order, storefront_order])
    db.session.flush()

    db.session.add_all([
        OrderItem(
            order_id=manual_order.id,
            product_id=manual_product.id,
            quantity=1,
            unit_price=Decimal('100.00'),
            subtotal=Decimal('100.00')
        ),
        OrderItem(
            order_id=storefront_order.id,
            product_id=storefront_product.id,
            quantity=2,
            unit_price=Decimal('100.00'),
            subtotal=Decimal('200.00')
        )
    ])
    db.session.commit()

    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow()
    metrics = BusinessMetrics(user_id=user.id).get_financial_health(
        start_date=start_date,
        end_date=end_date
    )

    revenue_split = metrics['revenue']['source_breakdown']
    profitability_split = metrics['profitability']['source_breakdown']

    assert revenue_split['manual']['revenue'] == 116.0
    assert revenue_split['storefront']['revenue'] == 232.0
    assert revenue_split['combined']['revenue'] == 348.0

    assert profitability_split['manual']['gross_profit'] == 60.0
    assert profitability_split['storefront']['gross_profit'] == 140.0
    assert profitability_split['storefront']['tax'] == 32.0
    assert profitability_split['combined']['gross_profit'] == 200.0

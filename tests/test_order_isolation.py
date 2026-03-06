from app.models import User, Customer, Order


def _login_client(client, user: User):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_orders_index_only_shows_current_user_orders(client, db):
    user_one = User(username='owner-a', email='owner-a@example.com', confirmed=True)
    user_two = User(username='owner-b', email='owner-b@example.com', confirmed=True)
    db.session.add_all([user_one, user_two])
    db.session.flush()

    customer_one = Customer(user_id=user_one.id, name='Customer One')
    customer_two = Customer(user_id=user_two.id, name='Customer Two')
    db.session.add_all([customer_one, customer_two])
    db.session.flush()

    order_one = Order(
        user_id=user_one.id,
        customer_id=customer_one.id,
        order_number='ORD-OWNER-A-001',
        status=Order.STATUS_PENDING
    )
    order_two = Order(
        user_id=user_two.id,
        customer_id=customer_two.id,
        order_number='ORD-OWNER-B-001',
        status=Order.STATUS_PENDING
    )
    db.session.add_all([order_one, order_two])
    db.session.commit()

    _login_client(client, user_one)
    response = client.get('/orders/')

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'ORD-OWNER-A-001' in body
    assert 'ORD-OWNER-B-001' not in body


def test_orders_api_create_rejects_foreign_customer(client, db):
    owner = User(username='orders-owner', email='orders-owner@example.com', confirmed=True)
    other_user = User(username='orders-other', email='orders-other@example.com', confirmed=True)
    db.session.add_all([owner, other_user])
    db.session.flush()

    foreign_customer = Customer(user_id=other_user.id, name='Foreign Customer')
    db.session.add(foreign_customer)
    db.session.commit()

    _login_client(client, owner)
    response = client.post(
        '/api/v1/orders/',
        json={
            'customer_id': foreign_customer.id,
            'status': Order.STATUS_PENDING
        },
        headers={'X-API-KEY': 'test-api-key'}
    )

    assert response.status_code == 404
    assert Order.query.filter_by(user_id=owner.id).count() == 0

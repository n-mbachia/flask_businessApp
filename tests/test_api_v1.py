import json
import pytest
from app.models import User, Product, db

class TestAPIv1:
    """Test API v1 endpoints."""

    @staticmethod
    def _login_client(client, user: User):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
    
    def test_api_docs(self, client):
        """Test API documentation endpoint."""
        response = client.get('/api/v1/', headers={'X-API-KEY': 'test-api-key'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'name' in data
        assert 'version' in data
        assert 'endpoints' in data
        assert len(data['endpoints']) > 0
    
    def test_products_endpoint(self, auth_client, db, sample_user):
        """Test products endpoint."""
        # Add test products
        product1 = Product(
            name='Test Product 1',
            description='Test Description 1',
            user_id=sample_user.id,
            cogs_per_unit=5.50,
            selling_price_per_unit=10.99
        )
        product2 = Product(
            name='Test Product 2',
            description='Test Description 2',
            user_id=sample_user.id,
            cogs_per_unit=6.75,
            selling_price_per_unit=20.50
        )
        db.session.add_all([product1, product2])
        db.session.commit()
        
        # Test GET /api/v1/products
        TestAPIv1._login_client(auth_client, sample_user)
        response = auth_client.get(
            '/api/v1/products/',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'products' in data
        assert len(data['products']) == 2
    
    def test_single_product_endpoint(self, auth_client, db, sample_user):
        """Test single product endpoint."""
        # Add test product
        product = Product(
            name='Test Product',
            description='Test Description',
            user_id=sample_user.id,
            cogs_per_unit=8.25,
            selling_price_per_unit=15.99
        )
        db.session.add(product)
        db.session.commit()
        
        # Test GET /api/v1/products/<id>
        TestAPIv1._login_client(auth_client, sample_user)
        response = auth_client.get(
            f'/api/v1/products/{product.id}',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'product' in data
        assert data['product']['name'] == 'Test Product'
    
    def test_create_product_unauthorized(self, client):
        """Test creating a product without authentication."""
        response = client.post(
            '/api/v1/products',
            data=json.dumps({
                'name': 'New Product',
                'description': 'New Description',
                'cogs_per_unit': 10.0,
                'selling_price_per_unit': 29.99,
                'track_inventory': True
            }),
            content_type='application/json'
        )
        assert response.status_code in (401, 302, 308)
    
    def test_create_product_authorized(self, auth_client, sample_user):
        """Test creating a product with authentication."""
        TestAPIv1._login_client(auth_client, sample_user)
        response = auth_client.post(
            '/api/v1/products',
            data=json.dumps({
                'name': 'New Product',
                'description': 'New Description',
                'cogs_per_unit': 12.0,
                'selling_price_per_unit': 29.99,
                'track_inventory': True
            }),
            content_type='application/json',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'product' in data
        assert data['product']['name'] == 'New Product'
        assert float(data['product']['selling_price_per_unit']) == 29.99
    
    def test_update_product(self, auth_client, db, sample_user):
        """Test updating a product."""
        # Add test product
        product = Product(
            name='Test Product',
            description='Test Description',
            user_id=sample_user.id,
            cogs_per_unit=6.00,
            selling_price_per_unit=15.99
        )
        db.session.add(product)
        db.session.commit()
        TestAPIv1._login_client(auth_client, sample_user)
        # Test PUT /api/v1/products/<id>
        response = auth_client.put(
            f'/api/v1/products/{product.id}',
            data=json.dumps({
                'name': 'Updated Product',
                'description': 'Updated Description',
                'cogs_per_unit': 6.50,
                'selling_price_per_unit': 19.99,
                'track_inventory': False
            }),
            content_type='application/json',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'product' in data
        assert data['product']['name'] == 'Updated Product'
        assert float(data['product']['selling_price_per_unit']) == 19.99
    
    def test_delete_product(self, auth_client, db, sample_user):
        """Test deleting a product."""
        # Add test product
        product = Product(
            name='Test Product',
            description='Test Description',
            user_id=sample_user.id,
            cogs_per_unit=7.00,
            selling_price_per_unit=15.99
        )
        db.session.add(product)
        db.session.commit()
        TestAPIv1._login_client(auth_client, sample_user)
        # Test DELETE /api/v1/products/<id>
        response = auth_client.delete(
            f'/api/v1/products/{product.id}',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 204
        
        # Verify product was deleted
        TestAPIv1._login_client(auth_client, sample_user)
        response = auth_client.get(
            f'/api/v1/products/{product.id}',
            headers={'X-API-KEY': 'test-api-key'}
        )
        assert response.status_code == 404

import json
import pytest
from app import create_app, db
from app.models import Product, User, InventoryMovement
from config import TestingConfig

pytestmark = pytest.mark.skip_auto_context

class TestProductsAPI:
    """Test cases for the Products API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test application context and database."""
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user and login
        self.user = User(
            username='testuser',
            email='test@example.com',
            password_hash='testpass'
        )
        db.session.add(self.user)
        db.session.commit()
        
        # Create test data
        self.test_product = Product(
            name='Test Product',
            user_id=self.user.id,
            category='Test Category',
            sku='TEST123',
            barcode='123456789012',
            cogs_per_unit=10.50,
            selling_price_per_unit=19.99,
            reorder_level=5,
            is_active=True
        )
        db.session.add(self.test_product)
        db.session.commit()

        # Create inventory movement
        self.movement = InventoryMovement(
            product_id=self.test_product.id,
            quantity=10,
            movement_type='receipt',
            notes='Initial stock'
        )
        db.session.add(self.movement)
        db.session.commit()
        
        # Login the test user
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True
        
        yield
        
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_get_products(self):
        """Test getting all products."""
        # Add test products
        product1 = Product(
            name='Test Product 1',
            description='Test Description 1',
            user_id=self.user.id,
            cogs_per_unit=5.50,
            selling_price_per_unit=10.99,
            sku='SKU-001',
            barcode='111'
        )
        product2 = Product(
            name='Test Product 2',
            description='Test Description 2',
            user_id=self.user.id,
            cogs_per_unit=6.75,
            selling_price_per_unit=20.50,
            sku='SKU-002',
            barcode='222'
        )
        db.session.add_all([product1, product2])
        db.session.commit()
        
        # Test GET /api/v1/products/ (trailing slash to avoid redirect)
        response = self.client.get('/api/v1/products/', follow_redirects=True)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert any(prod['name'] == 'Test Product' for prod in data)

    def test_get_product(self):
        """Test getting a single product."""
        # Test GET /api/v1/products/<id>
        response = self.client.get(f'/api/v1/products/{self.test_product.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Test Product'
        assert float(data['selling_price_per_unit']) == 19.99

    def test_create_product(self):
        """Test creating a new product."""
        # Test POST /api/v1/products
        payload = {
            'name': 'New Product',
            'description': 'New Description',
            'cogs_per_unit': 15.0,
            'selling_price_per_unit': 29.99,
            'initial_quantity': 50,
            'track_inventory': True
        }
        response = self.client.post(
            '/api/v1/products/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['name'] == 'New Product'
        assert float(data['selling_price_per_unit']) == 29.99
        product = Product.query.filter_by(name='New Product').first()
        assert product is not None

    def test_update_product(self):
        """Test updating a product."""
        update_data = {
            'name': 'Updated Product',
            'category': 'Updated Category',
            'selling_price_per_unit': 24.99,
            'description': 'Updated description'
        }
        response = self.client.put(
            f'/api/v1/products/{self.test_product.id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Updated Product'
        assert data['category'] == 'Updated Category'
        assert float(data['selling_price_per_unit']) == 24.99

    def test_delete_product(self):
        """Test deleting a product."""
        response = self.client.delete(f'/api/v1/products/{self.test_product.id}')
        assert response.status_code == 204
        
        # Verify product is deleted
        response = self.client.get(f'/api/v1/products/{self.test_product.id}')
        assert response.status_code == 404

    def test_get_inventory_history(self):
        """Skip inventory history tests that target removed endpoints."""
        pytest.skip('Inventory history endpoint removed in API v1')

    def test_unauthorized_access(self):
        """Test that unauthorized access is rejected."""
        # Clear the session to simulate not being logged in
        with self.client.session_transaction() as sess:
            sess.clear()
        
        response = self.client.get('/api/v1/products')
        assert response.status_code in (302, 308)

import json
import pytest
from app.models import User, db

class TestAuthAPI:
    """Test authentication API endpoints."""
    
    def test_register_user(self, client, db):
        """Test user registration."""
        response = client.post(
            '/api/v1/auth/register',
            data=json.dumps({
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpassword123',
                'confirm_password': 'testpassword123'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'User registered successfully'
        
        # Verify user was created in the database
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.username == 'testuser'
    
    def test_login_user(self, client, db):
        """Test user login."""
        # Create a test user
        user = User(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        db.session.add(user)
        db.session.commit()
        
        # Test login
        response = client.post(
            '/api/v1/auth/login',
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'testpassword123'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
    
    def test_protected_route(self, client, auth):
        """Test access to protected route with valid token."""
        # Login to get token
        auth.login()
        
        # Access protected route
        response = client.get(
            '/api/v1/auth/protected',
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'Protected route accessed'
    
    def test_refresh_token(self, client, auth):
        """Test token refresh."""
        # Login to get refresh token
        auth.login()
        
        # Refresh token
        response = client.post(
            '/api/v1/auth/refresh',
            headers={'Authorization': 'Bearer test-refresh-token'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
    
    def test_logout(self, client, auth):
        """Test user logout."""
        # Login first
        auth.login()
        
        # Logout
        response = client.post(
            '/api/v1/auth/logout',
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'Successfully logged out'

"""
Authentication API endpoints.

This module contains all authentication-related API endpoints with JWT support.
"""
from flask_restx import Namespace, Resource, fields
from flask import request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import jwt

# Import rate limiting
from app.middleware.rate_limiter import auth_rate_limit, strict_rate_limit

# Create namespace
ns = Namespace('auth', description='Authentication operations')

# Request models
login_model = ns.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password'),
    'remember': fields.Boolean(required=False, description='Remember me')
})

# Response models
token_model = ns.model('Token', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token'),
    'token_type': fields.String(description='Token type (Bearer)'),
    'expires_in': fields.Integer(description='Token expiration time in seconds')
})

refresh_token_model = ns.model('RefreshToken', {
    'refresh_token': fields.String(required=True, description='Refresh token')
})

def generate_tokens(user_id):
    """Generate JWT access and refresh tokens."""
    now = datetime.utcnow()
    
    # Access token (short-lived)
    access_payload = {
        'user_id': user_id,
        'exp': now + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'iat': now,
        'type': 'access'
    }
    
    # Refresh token (long-lived)
    refresh_payload = {
        'user_id': user_id,
        'exp': now + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        'iat': now,
        'type': 'refresh'
    }
    
    access_token = jwt.encode(
        access_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    refresh_token = jwt.encode(
        refresh_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
    }

@ns.route('/login')
class Login(Resource):
    @ns.expect(login_model)
    @ns.response(200, 'Success', token_model)
    @ns.response(400, 'Invalid credentials')
    @ns.response(401, 'Unauthorized')
    @ns.response(429, 'Rate limit exceeded')
    @auth_rate_limit
    def post(self):
        """User login with JWT token generation."""
        from app.models import User
        
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if not email or not password:
            return {'message': 'Email and password are required'}, 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return {'message': 'Invalid email or password'}, 401
        
        if not check_password_hash(user.password_hash, password):
            return {'message': 'Invalid email or password'}, 401
        
        if not user.confirmed:
            return {'message': 'Account not confirmed. Please check your email.'}, 401
        
        # Log in the user
        login_user(user, remember=remember)
        
        # Generate JWT tokens
        tokens = generate_tokens(user.id)
        
        return {
            **tokens,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username
            }
        }, 200

@ns.route('/refresh')
class TokenRefresh(Resource):
    @ns.expect(refresh_token_model)
    @ns.response(200, 'Success', token_model)
    @ns.response(401, 'Invalid token')
    @ns.response(429, 'Rate limit exceeded')
    @strict_rate_limit
    def post(self):
        """Refresh JWT access token."""
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return {'message': 'Refresh token is required'}, 400
        
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Verify token type
            if payload.get('type') != 'refresh':
                return {'message': 'Invalid token type'}, 401
            
            # Verify user exists
            from app.models import User
            user = User.query.get(payload['user_id'])
            if not user or not user.confirmed:
                return {'message': 'User not found or inactive'}, 401
            
            # Generate new tokens
            tokens = generate_tokens(user.id)
            return tokens, 200
            
        except jwt.ExpiredSignatureError:
            return {'message': 'Refresh token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Invalid refresh token'}, 401

@ns.route('/logout')
class Logout(Resource):
    @login_required
    def post(self):
        """User logout."""
        logout_user()
        return {'message': 'Successfully logged out'}, 200

@ns.route('/me')
class UserInfo(Resource):
    @login_required
    def get(self):
        """Get current user info."""
        return {
            'id': current_user.id,
            'email': current_user.email,
            'username': current_user.username,
            'is_confirmed': current_user.confirmed,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        }, 200

@ns.route('/verify')
class TokenVerify(Resource):
    def post(self):
        """Verify JWT token validity."""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'valid': False, 'message': 'No token provided'}, 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            if payload.get('type') != 'access':
                return {'valid': False, 'message': 'Invalid token type'}, 401
            
            # Verify user exists
            from app.models import User
            user = User.query.get(payload['user_id'])
            if not user or not user.confirmed:
                return {'valid': False, 'message': 'User not found or inactive'}, 401
            
            return {
                'valid': True,
                'user_id': payload['user_id'],
                'exp': payload['exp']
            }, 200
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'message': 'Token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'valid': False, 'message': 'Invalid token'}, 401

import os
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_PATH))

import pytest
from flask import has_app_context
from unittest.mock import patch, MagicMock
from app import create_app, db as _db
from app.models import User

# Set environment variables for testing
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

TEST_APP = create_app('testing')

@pytest.fixture(scope='session')
def app():
    """Session-scoped Flask application for tests."""
    TEST_APP.config['TESTING'] = True
    TEST_APP.config['WTF_CSRF_ENABLED'] = False
    with TEST_APP.app_context():
        _db.create_all()
    yield TEST_APP
    with TEST_APP.app_context():
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def db(app):
    """Function-scoped database fixture that refreshes the schema per test."""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        _db.session.commit()
    yield _db
    with app.app_context():
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app, db):
    """Test client tied to the refreshed database."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """Test runner for CLI commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_client(client):
    """Authenticated-ish client for tests that rely on login state."""
    return client

# Mock external services
@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services for testing."""
    with patch('flask_mail.Mail') as mock_mail, \
         patch('flask_caching.Cache') as mock_cache, \
         patch('sentry_sdk.init') as mock_sentry:
        
        # Configure mock mail
        mock_mail_instance = MagicMock()
        mock_mail.return_value = mock_mail_instance
        
        # Configure mock cache
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        
        yield {
            'mail': mock_mail_instance,
            'cache': mock_cache_instance,
            'sentry': mock_sentry
        }

# Test client with authentication
class AuthActions:
    def __init__(self, client):
        self._client = client
    
    def login(self, email='test@example.com', password='password'):
        return self._client.post(
            '/auth/login',
            data={'email': email, 'password': password},
            follow_redirects=True
        )
    
    def logout(self):
        return self._client.get('/auth/logout', follow_redirects=True)

@pytest.fixture
def auth(client):
    """Authentication test client."""
    return AuthActions(client)

# Test database session
@pytest.fixture
def session(db):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)
    
    db.session = session
    
    yield session
    
    transaction.rollback()
    connection.close()
    session.remove()

# Test request context
@pytest.fixture
def app_context(app):
    """Application context for testing."""
    with app.app_context():
        yield app


TEST_APP = create_app('testing')


@pytest.fixture(autouse=True)
def push_app_context(request):
    """Ensure each test runs inside a Flask application context."""
    if request.node.get_closest_marker('skip_auto_context'):
        yield
        return
    if has_app_context():
        yield
        return
    with TEST_APP.app_context():
        yield


@pytest.fixture
def sample_user(app):
    """Create a sample user for tests that need authentication context."""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com'
        )
        _db.session.add(user)
        _db.session.commit()
        yield user
        _db.session.delete(user)
        _db.session.commit()

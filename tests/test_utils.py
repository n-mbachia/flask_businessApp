import logging
from datetime import datetime
from flask import Flask, template_rendered
from contextlib import contextmanager

from app.utils import (
    configure_logging,
    register_context_processors,
    register_template_filters
)

def test_configure_logging(app):
    """Test logging configuration."""
    # Test debug logging
    app.config['DEBUG'] = True
    configure_logging(app)
    assert app.logger.level == logging.DEBUG
    
    # Test production logging
    app.config['DEBUG'] = False
    configure_logging(app)
    assert app.logger.level == logging.INFO

def test_register_context_processors(app):
    """Test that context processors are registered correctly."""
    register_context_processors(app)
    
    # Test template rendering with context processors
    with app.test_request_context():
        # Test now context processor
        assert 'now' in app.jinja_env.globals
        assert isinstance(app.jinja_env.globals['now'](), datetime)
        
        # Test current_year context processor
        assert 'current_year' in app.jinja_env.globals
        assert isinstance(app.jinja_env.globals['current_year'](), int)
        
        # Test template variables
        assert 'app_name' in app.jinja_env.globals
        assert 'debug' in app.jinja_env.globals
        assert 'config' in app.jinja_env.globals

def test_register_template_filters(app):
    """Test that template filters are registered correctly."""
    register_template_filters(app)
    
    # Test number formatting
    assert app.jinja_env.filters['number'](1000) == '1,000'
    assert app.jinja_env.filters['number'](1234.5678, 2) == '1,234.57'
    
    # Test currency formatting
    assert app.jinja_env.filters['currency'](19.99) == '$19.99'
    assert app.jinja_env.filters['currency'](19.99, '€') == '€19.99'
    
    # Test date formatting
    test_date = datetime(2023, 5, 15)
    assert app.jinja_env.filters['date'](test_date) == '2023-05-15'
    assert app.jinja_env.filters['date'](test_date, '%b %d, %Y') == 'May 15, 2023'
    
    # Test datetime formatting
    test_datetime = datetime(2023, 5, 15, 14, 30)
    assert app.jinja_env.filters['datetime'](test_datetime) == '2023-05-15 14:30'
    assert app.jinja_env.filters['datetime'](test_datetime, '%Y-%m-%d %H:%M:%S') == '2023-05-15 14:30:00'
    
    # Test safe HTML rendering
    html = '<div>Test</div>'
    from markupsafe import Markup
    assert isinstance(app.jinja_env.filters['safe'](html), Markup)
    assert str(app.jinja_env.filters['safe'](html)) == html

def test_error_handlers(client):
    """Test error handlers."""
    # Test 404 error
    response = client.get('/non-existent-route')
    assert response.status_code == 404
    
    # Test 500 error
    @client.application.route('/test-500')
    def trigger_500():
        1 / 0
    
    response = client.get('/test-500')
    assert response.status_code == 500
    
    # Test API error response
    response = client.get(
        '/api/non-existent-endpoint',
        headers={'Accept': 'application/json'}
    )
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'message' in data

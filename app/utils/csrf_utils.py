"""
CSRF Utilities

This module provides utility functions for CSRF token handling.
"""
from flask import request, current_app
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms import ValidationError

def get_csrf_token():
    """Get the current CSRF token."""
    return generate_csrf()

def validate_csrf_token():
    """
    Validate the CSRF token from the request.
    
    Returns:
        bool: True if the token is valid, False otherwise
    """
    try:
        # Get token from form data or headers
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        if not token:
            return False
            
        validate_csrf(token)
        return True
    except (ValidationError, KeyError):
        return False

def csrf_exempt(view):
    """Decorator to mark a view as CSRF exempt."""
    view.csrf_exempt = True
    return view

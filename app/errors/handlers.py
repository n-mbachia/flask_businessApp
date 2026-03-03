"""
Error handlers for the application.

This module contains error handlers and utility functions for handling
HTTP errors and exceptions across the application.
"""

from flask import render_template, jsonify, request
from werkzeug.exceptions import HTTPException
import logging

def register_error_handlers(app):
    """Register error handlers with the Flask application.
    
    Args:
        app: The Flask application instance.
    """
    # Handle 404 errors
    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.'
            }), 404
        return render_template('errors/404.html'), 404

    # Handle 500 errors
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 Error: {error}')
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An internal server error occurred.'
            }), 500
        return render_template('errors/500.html'), 500

    # Handle 403 errors
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.'
            }), 403
        return render_template('errors/403.html'), 403

    # Handle 401 errors
    @app.errorhandler(401)
    def unauthorized_error(error):
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Please log in to access this resource.'
            }), 401
        return render_template('errors/401.html'), 401

    # Handle other HTTP exceptions
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': error.name,
                'message': error.description
            }), error.code
        return render_template('errors/error.html', error=error), error.code

    # Handle generic exceptions
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled Exception: {error}', exc_info=True)
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred.'
            }), 500
        return render_template('errors/500.html'), 500

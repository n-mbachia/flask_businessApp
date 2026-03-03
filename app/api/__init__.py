"""
API package for the application.

This package contains all API-related functionality, including versioned API blueprints.
"""
from flask import Blueprint, jsonify, current_app
from werkzeug.exceptions import HTTPException
import logging

def register_blueprints(app):
    """Register all API blueprints with the application."""
    try:
        # Import blueprints here to avoid circular imports
        from .v1 import api_v1_bp, register_namespaces
        
        # Register blueprints
        app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
        
        # Register API namespaces
        register_namespaces()
        
        # Register API error handlers
        register_api_error_handlers(app)
        
        return True
    except Exception as e:
        # Use logging instead of current_app.logger to avoid context issues
        logging.error(f"Failed to register API blueprints: {str(e)}")
        # Re-raise the exception to ensure it's not silently ignored
        raise

def register_api_error_handlers(app):
    """Register error handlers for the API."""
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            'success': False,
            'error': 'bad_request',
            'message': str(error) or 'Bad request',
            'status': 400
        }), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({
            'success': False,
            'error': 'unauthorized',
            'message': str(error) or 'Unauthorized',
            'status': 401
        }), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'message': str(error) or 'Forbidden',
            'status': 403
        }), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'success': False,
            'error': 'not_found',
            'message': str(error) or 'Resource not found',
            'status': 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({
            'success': False,
            'error': 'method_not_allowed',
            'message': str(error) or 'Method not allowed',
            'status': 405
        }), 405

    @app.errorhandler(422)
    def unprocessable_entity_error(error):
        return jsonify({
            'success': False,
            'error': 'unprocessable_entity',
            'message': str(error) or 'Unprocessable entity',
            'status': 422
        }), 422

    @app.errorhandler(429)
    def too_many_requests_error(error):
        return jsonify({
            'success': False,
            'error': 'too_many_requests',
            'message': str(error) or 'Too many requests',
            'status': 429
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'success': False,
            'error': 'internal_server_error',
            'message': 'An internal server error occurred',
            'status': 500
        }), 500

    # Handle other exceptions
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Use logging instead of app.logger to avoid context issues
        logging.error(f"Unhandled exception: {str(error)}")
        
        # Return a generic error response
        return jsonify({
            'success': False,
            'error': 'internal_server_error',
            'message': 'An unexpected error occurred',
            'status': 500
        }), 500

__all__ = ['register_blueprints']

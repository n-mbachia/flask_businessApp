# app/routes/errors.py

"""
Error Handlers

This module contains error handlers for the application.
"""
from flask import jsonify, render_template, request, current_app
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        # Sanitize error message
        safe_message = "Invalid request parameters" if "Invalid request" in str(error) else "Bad request"
        logger.warning(f'400 Bad Request: {str(error)}')
        
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Bad Request',
                'message': safe_message,
                'status': 400
            }), 400
        return render_template('errors/400.html', error=safe_message), 400

    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f'403 Forbidden: {request.path}')
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.',
                'status': 403
            }), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f'404 Not Found: {request.path}')
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.',
                'status': 404
            }), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.warning('413 Request Entity Too Large')
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Request Entity Too Large',
                'message': 'The request exceeds the maximum allowed size.',
                'status': 413
            }), 413
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        logger.warning('429 Too Many Requests')
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Too Many Requests',
                'message': 'You have made too many requests. Please try again later.',
                'status': 429
            }), 429
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'500 Internal Server Error: {str(error)}', exc_info=True)
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred on the server.',
                'status': 500
            }), 500
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Pass through HTTP exceptions
        if isinstance(error, HTTPException):
            return error
            
        # Log the error
        logger.error(f'Unhandled Exception: {str(error)}', exc_info=True)
        
        # Return JSON or render template based on request type
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred on the server.',
                'status': 500
            }), 500
            
        return render_template('errors/500.html', error=error), 500

    logger.info("Error handlers registered successfully")

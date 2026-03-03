from flask import render_template, request, jsonify, current_app
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'bad_request',
                'message': str(error) or 'Bad request',
                'status_code': 400
            }), 400
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'unauthorized',
                'message': str(error) or 'Authentication required',
                'status_code': 401
            }), 401
        return render_template('errors/401.html', error=error), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'forbidden',
                'message': str(error) or 'You do not have permission to access this resource',
                'status_code': 403
            }), 403
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'not_found',
                'message': str(error) or 'The requested resource was not found',
                'status_code': 404
            }), 404
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 Method Not Allowed errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'method_not_allowed',
                'message': str(error) or 'The method is not allowed for the requested URL',
                'status_code': 405
            }), 405
        return render_template('errors/405.html', error=error), 405

    @app.errorhandler(409)
    def conflict_error(error):
        """Handle 409 Conflict errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'conflict',
                'message': str(error) or 'A conflict occurred while processing your request',
                'status_code': 409
            }), 409
        return render_template('errors/409.html', error=error), 409

    @app.errorhandler(413)
    def request_entity_too_large_error(error):
        """Handle 413 Request Entity Too Large errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'request_entity_too_large',
                'message': str(error) or 'The request is larger than the server is willing or able to process',
                'status_code': 413
            }), 413
        return render_template('errors/413.html', error=error), 413

    @app.errorhandler(422)
    def unprocessable_entity_error(error):
        """Handle 422 Unprocessable Entity errors (used by webargs)."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'unprocessable_entity',
                'message': str(error) or 'The request was well-formed but was unable to be followed due to semantic errors',
                'status_code': 422,
                'errors': getattr(error, 'data', {}).get('messages', {})
            }), 422
        return render_template('errors/422.html', error=error), 422

    @app.errorhandler(429)
    def ratelimit_error(error):
        """Handle 429 Too Many Requests errors."""
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'too_many_requests',
                'message': str(error) or 'Too many requests, please try again later',
                'status_code': 429
            }), 429
        return render_template('errors/429.html', error=error), 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        from . import db  # Moved import here to avoid circular imports
        db.session.rollback()
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'internal_server_error',
                'message': str(error) or 'An unexpected error occurred',
                'status_code': 500
            }), 500
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """
        Handle exceptions that don't have a specific error handler.
        """
        # Pass through HTTP errors
        if isinstance(error, HTTPException):
            return error
        
        # Log the error
        app.logger.error(f'Unhandled exception: {str(error)}', exc_info=True)
        
        # Return JSON response for API requests
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'internal_server_error',
                'message': 'An unexpected error occurred',
                'status_code': 500
            }), 500
            
        # Return HTML response for web requests
        return render_template('errors/500.html', error=error), 500

# app/utils/decorators.py

import os
import functools
import logging
import time
from typing import Callable, Any, Optional, List, TypeVar, ParamSpec
from http import HTTPStatus
from flask import jsonify, current_app, flash, redirect, url_for, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _HAS_FLASK_LIMITER = True
except ImportError:
    Limiter = None
    get_remote_address = None
    _HAS_FLASK_LIMITER = False

try:
    from sentry_sdk import capture_message
    _HAS_SENTRY = True
except ImportError:
    capture_message = None
    _HAS_SENTRY = False

P = ParamSpec('P')
F = TypeVar('F', bound=Callable[..., Any])

# Configure rate limiter
if _HAS_FLASK_LIMITER:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://"
    )
else:
    limiter = None

def performance_log(func: F) -> F:
    """
    Logs the duration of a function call with user and path info.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logging.info(
                f"[PERFORMANCE] {func.__module__}.{func.__name__} "
                f"| Duration: {duration:.4f}s "
                f"| User: {getattr(current_user, 'id', 'anonymous')} "
                f"| Path: {request.path}"
            )
            return result
        except Exception as e:
            logging.error(
                f"[PERFORMANCE ERROR] {func.__module__}.{func.__name__} "
                f"| Error: {str(e)} "
                f"| User: {getattr(current_user, 'id', 'anonymous')}",
                exc_info=True
            )
            # Capture error in Sentry if configured
            if current_app.config.get("SENTRY_DSN"):
                capture_message(f"Performance error in {func.__name__}: {str(e)}")
            raise
    return wrapper

def track_performance(metric_name: str) -> Callable[[F], F]:
    """
    Tracks performance and sends metrics to Sentry if configured.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time

                logging.info(
                    f"[METRIC] {metric_name}: {duration:.4f}s "
                    f"| Function: {func.__module__}.{func.__name__} "
                    f"| User: {getattr(current_user, 'id', 'anonymous')}")

                if current_app.config.get("SENTRY_DSN"):
                    try:
                        from sentry_sdk import metrics
                        metrics.distribution(
                            key=f"performance.{metric_name}",
                            value=duration,
                            unit="seconds"
                        )
                    except Exception as e:
                        current_app.logger.warning(
                            f"[SENTRY METRIC ERROR] {e}",
                            exc_info=True
                        )

                return result
            except Exception as e:
                logging.error(
                    f"[TRACK ERROR] {metric_name} | {func.__module__}.{func.__name__} "
                    f"| Error: {str(e)} "
                    f"| User: {getattr(current_user, 'id', 'anonymous')}",
                    exc_info=True
                )
                # Capture error in Sentry
                if current_app.config.get("SENTRY_DSN"):
                    capture_message(f"Tracking error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

def handle_exceptions(func: F) -> F:
    """
    Handles and logs exceptions with user-friendly response.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(
                f"[EXCEPTION] {func.__module__}.{func.__name__}: {str(e)}",
                exc_info=True
            )
            # Capture error in Sentry
            if current_app.config.get("SENTRY_DSN"):
                capture_message(f"Exception in {func.__name__}: {str(e)}")
            
            # Return appropriate error response
            if isinstance(e, HTTPException):
                status_code = e.code
            elif hasattr(e, 'status_code'):
                status_code = e.status_code
            else:
                status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            
            error_data = {
                'status': 'error',
                'message': str(e),
                'code': status_code
            }
            
            return jsonify(error_data), status_code
    return wrapper

def handle_api_errors(func: F) -> F:
    """
    Handles API errors and returns consistent JSON responses.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'code': HTTPStatus.BAD_REQUEST
            }), HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"API Error: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'An internal server error occurred',
                'code': HTTPStatus.INTERNAL_SERVER_ERROR
            }), HTTPStatus.INTERNAL_SERVER_ERROR
    return wrapper

def role_required(roles: List[str]) -> Callable[[F], F]:
    """
    Restricts route access to users with specific roles.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not any(role in current_user.roles for role in roles):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.index'))
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

'''
def check_confirmed(func):
    """
    Decorator to check if the current user has confirmed their email.
    In development mode (when DEBUG is True or ENV is 'development'), this check is bypassed.
    In production, redirects to the unconfirmed page if the user's email is not confirmed.
    """
    @functools.wraps(func)
    def decorated_function(*args, **kwargs):
        # Bypass check in development mode
        if current_app.debug or current_app.config.get('ENV') == 'development':
            return func(*args, **kwargs)
            
        # In production, check if user is confirmed
        if current_user.is_anonymous or not current_user.confirmed:
            flash('Please confirm your account to access this page.', 'warning')
            return redirect(url_for('auth.unconfirmed'))
        return func(*args, **kwargs)
    return decorated_function'''

def check_confirmed(func):
    @functools.wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get('REQUIRE_EMAIL_CONFIRMATION', False):
            return func(*args, **kwargs)

        is_dev = (
            current_app.debug or
            os.environ.get('FLASK_ENV') == 'development' or
            current_app.config.get('ENV') == 'development'
        )
        if is_dev:
            return func(*args, **kwargs)

        if current_user.is_anonymous or not current_user.confirmed:
            flash('Please confirm your account to access this page.', 'warning')
            return redirect(url_for('auth.unconfirmed'))

        return func(*args, **kwargs)
    return decorated_function

def rate_limit(max_calls: int, period: int = 60) -> Callable[[F], F]:
    """
    Limits route usage per IP or user within the given time period.
    Uses Flask-Limiter's built-in functionality.
    """
    def decorator(func: F) -> F:
        # Create a rate limit string (e.g., '5 per minute')
        rate_limit_str = f"{max_calls} per {period} seconds"
        
        # Apply the rate limit using Flask-Limiter's decorator
        limited_func = limiter.limit(rate_limit_str)(func)
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return limited_func(*args, **kwargs)
            except Exception as e:
                # Handle rate limit exceeded
                if hasattr(e, 'description') and 'rate limit' in e.description.lower():
                    error_data = {
                        'status': 'error',
                        'message': 'Rate limit exceeded. Please try again later.',
                        'code': HTTPStatus.TOO_MANY_REQUESTS
                    }
                    return jsonify(error_data), HTTPStatus.TOO_MANY_REQUESTS
                raise
        
        return wrapper
    return decorator

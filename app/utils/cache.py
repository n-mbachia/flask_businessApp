# app/utils/cache.py

"""
Caching utilities for the application.

This module provides a centralized cache interface using Flask-Caching with SimpleCache as the default backend.
It includes utility functions for common caching patterns and automatic cache key generation.
"""

from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import hashlib
from flask import current_app
from flask_caching import Cache

# Type variable for generic function type
F = TypeVar('F', bound=Callable[..., Any])


def _get_primary_cache() -> Optional[Cache]:
    """Get the application's primary Flask-Caching instance if available."""
    try:
        from app import cache as app_cache
        if app_cache and hasattr(app_cache, 'get') and hasattr(app_cache, 'set'):
            return app_cache
    except Exception:
        pass
    return None

def init_cache(app) -> Cache:
    """
    Initialize the cache with the Flask app.

    Args:
        app: The Flask application instance

    Returns:
        Cache: The initialized cache instance with required methods
    """
    # Default configuration - use simple cache
    config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    
    # Update with any app-specific config
    config.update(app.config.get_namespace('CACHE_'))
    
    app.logger.info(f"Initializing cache with config: {config}")
    
    # Initialize cache
    cache = Cache()
    
    try:
        # Initialize with config
        cache.init_app(app, config=config)
        
        # Test the cache
        with app.app_context():
            test_key = 'cache_test_key'
            try:
                # Test set and get operations
                cache.set(test_key, 'test_value', timeout=1)
                test_value = cache.get(test_key)
                if test_value != 'test_value':
                    app.logger.warning("Cache test failed: Incorrect value retrieved")
                    # Fall back to a simple dict-based cache
                    from werkzeug.contrib.cache import SimpleCache
                    cache = SimpleCache()
                else:
                    app.logger.info("Cache test passed")
            except Exception as e:
                app.logger.error(f"Cache test failed: {e}", exc_info=True)
                # Fall back to a simple dict-based cache
                from werkzeug.contrib.cache import SimpleCache
                cache = SimpleCache()
                
    except Exception as e:
        app.logger.error(f"Error initializing cache: {e}", exc_info=True)
        # Fall back to a simple dict-based cache
        from werkzeug.contrib.cache import SimpleCache
        cache = SimpleCache()
    
    # Ensure the cache object has the required methods
    if not hasattr(cache, 'get') or not hasattr(cache, 'set'):
        app.logger.warning("Cache object missing required methods, using SimpleCache")
        from werkzeug.contrib.cache import SimpleCache
        cache = SimpleCache()
    
    return cache

def get_cache() -> Cache:
    """
    Retrieve the cache instance from the current app context.

    Returns:
        Cache: The initialized cache instance.

    Raises:
        RuntimeError: If the cache is not initialized.
    """
    if not current_app:
        raise RuntimeError("No Flask application context is active.")
    
    # Prefer the globally initialized Flask-Caching extension.
    primary_cache = _get_primary_cache()
    if primary_cache is not None:
        return primary_cache

    # Fallback: legacy/project-specific cache initialization.
    try:
        cache = init_cache(current_app)
        return cache
    except Exception as e:
        current_app.logger.error(f"Failed to initialize fallback cache: {e}")
        raise

def generate_cache_key(f: F, *args: Any, **kwargs: Any) -> str:
    """
    Generate a unique cache key for a function call.

    Args:
        f: The function being called
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        str: A unique cache key
    """
    # Generate hash key based on function module, name, args, and kwargs
    key_parts = [f.__module__, f.__name__] + [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    raw_key = ":".join(key_parts)
    return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

def cached(timeout: int = 300, key_prefix: Optional[Union[str, Callable]] = None) -> Callable[[F], F]:
    """
    Decorator to cache function results.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Optional prefix for cache key (can be callable)

    Returns:
        Decorated function with caching
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            try:
                cache = get_cache()
                
                # Check if cache is properly initialized and has required methods
                if not hasattr(cache, 'get') or not hasattr(cache, 'set'):
                    current_app.logger.warning("Cache doesn't have required methods, skipping cache")
                    return f(*args, **kwargs)
                
                # Generate cache key
                if key_prefix is not None:
                    if callable(key_prefix):
                        try:
                            prefix = key_prefix(*args, **kwargs)
                        except TypeError:
                            prefix = key_prefix()
                    else:
                        prefix = key_prefix
                    cache_key = f"{prefix}_{f.__module__}_{f.__name__}"
                else:
                    cache_key = generate_cache_key(f, *args, **kwargs)
                
                current_app.logger.debug(f"Using cache key: {cache_key}")
                
                # Try to get from cache
                try:
                    cached_value = cache.get(cache_key)
                    if cached_value is not None:
                        current_app.logger.debug("Cache hit")
                        return cached_value
                    current_app.logger.debug("Cache miss")
                except Exception as e:
                    current_app.logger.error(f"Cache get failed: {e}", exc_info=True)
                
                # Call the actual function
                rv = f(*args, **kwargs)
                
                # Try to cache the result
                try:
                    current_app.logger.debug(f"Caching result with key: {cache_key}")
                    cache.set(cache_key, rv, timeout=timeout)
                except Exception as e:
                    current_app.logger.error(f"Cache set failed: {e}", exc_info=True)
                
                return rv
                
            except Exception as e:
                current_app.logger.error(f"Cache operation failed, calling function directly: {e}", exc_info=True)
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator

def clear_cache() -> bool:
    """
    Clear the entire cache.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache_obj = get_cache()
        if hasattr(cache_obj, 'clear'):
            return bool(cache_obj.clear())
        if hasattr(cache_obj, 'cache') and hasattr(cache_obj.cache, 'clear'):
            return bool(cache_obj.cache.clear())
        if current_app:
            current_app.logger.warning("Cache object does not expose clear().")
        return False
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Failed to clear cache: {e}")
        return False

def delete_memoized(f: F, *args: Any, **kwargs: Any) -> bool:
    """
    Delete a memoized function's cached result.

    Args:
        f: The memoized function
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache = get_cache()
        cache.delete_memoized(f, *args, **kwargs)
        return True
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Failed to delete memoized cache: {e}")
        return False

def invalidate_cache(key_prefix: Optional[str] = None) -> bool:
    """
    Invalidate cache entries matching a key prefix.

    Args:
        key_prefix: Optional prefix to match cache keys against

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache = get_cache()
        if not key_prefix:
            return bool(cache.clear())

        # SimpleCache backend does not support key iteration safely.
        # Fallback to full clear when a prefix is requested.
        return bool(cache.clear())
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Failed to invalidate cache: {e}")
        return False

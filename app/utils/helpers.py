# app/utils/helpers.py
"""
Helper Functions

This module contains various utility functions used throughout the application.
"""

import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, List, Dict, Union, Tuple
from flask import current_app, request, jsonify, render_template
from werkzeug.utils import secure_filename
import random
import string
from app.models import InventoryLot

logger = logging.getLogger(__name__)

def format_currency(amount: Optional[Union[float, int, str]]) -> str:
    """
    Format a number as a currency string.
    
    Args:
        amount: The amount to format
        
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return "N/A"
    try:
        amount_float = float(amount)
        formatted = f"{amount_float:,.2f}"
        # Use application's configured currency symbol
        currency_symbol = current_app.config.get('CURRENCY_SYMBOL', '$')
        return f"{currency_symbol}{formatted}"
    except (ValueError, TypeError):
        logger.warning(f"Invalid amount for currency formatting: {amount}")
        return str(amount)

def format_date(date_obj: Optional[datetime], format_str: str = '%Y-%m-%d') -> str:
    """
    Format a datetime object as a string.
    
    Args:
        date_obj: The datetime object to format
        format_str: Date format string
        
    Returns:
        str: Formatted date string
    """
    if not date_obj:
        return ""
    try:
        return date_obj.strftime(format_str)
    except (AttributeError, ValueError):
        logger.warning(f"Invalid date object: {date_obj}")
        return ""

def parse_date(date_str: Optional[str], format_str: str = '%Y-%m-%d') -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str: The date string to parse
        format_str: Date format string
        
    Returns:
        datetime: Parsed datetime object or None
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, format_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid date string: {date_str}")
        return None

def get_pagination(page: Optional[Union[str, int]] = None,
                   per_page: Optional[Union[str, int]] = None) -> Tuple[int, int]:
    """
    Get pagination parameters with defaults.
    
    Args:
        page: The page number
        per_page: Number of items per page
        
    Returns:
        Tuple[int, int]: (page, per_page)
    """
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1
    
    try:
        per_page = min(50, max(1, int(per_page or current_app.config.get('ITEMS_PER_PAGE', 10))))
    except (TypeError, ValueError):
        per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    
    return page, per_page

def json_response(data: Optional[Dict] = None,
                  message: str = "",
                  status: int = 200,
                  **kwargs: Any) -> Tuple[str, int]:
    """
    Create a standardized JSON response.
    
    Args:
        data: Response data
        message: Response message
        status: HTTP status code
        **kwargs: Additional response data
        
    Returns:
        Tuple[str, int]: JSON response and status code
    """
    response = {
        'status': 'success' if 200 <= status < 400 else 'error',
        'message': message,
        'data': data or {},
        **kwargs
    }
    return jsonify(response), status

def allowed_file(filename: str, allowed_extensions: Optional[set] = None) -> bool:
    """
    Check if a filename has an allowed extension.
    
    Args:
        filename: The filename to check
        allowed_extensions: Set of allowed extensions
        
    Returns:
        bool: True if file is allowed
    """
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename in lowercase.
    
    Args:
        filename: The filename
        
    Returns:
        str: File extension
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def get_week_range(date_obj: Optional[datetime] = None) -> Tuple[datetime.date, datetime.date]:
    """
    Get the start and end dates of the week containing the given date.
    
    Args:
        date_obj: The date to get week range for
        
    Returns:
        Tuple[datetime.date, datetime.date]: (start_date, end_date)
    """
    if date_obj is None:
        date_obj = datetime.utcnow()
    
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    
    return start.date(), end.date()

def get_month_range(date_obj: Optional[datetime] = None) -> Tuple[datetime.date, datetime.date]:
    """
    Get the start and end dates of the month containing the given date.
    
    Args:
        date_obj: The date to get month range for
        
    Returns:
        Tuple[datetime.date, datetime.date]: (start_date, end_date)
    """
    if date_obj is None:
        date_obj = datetime.utcnow()
    
    start = date_obj.replace(day=1)
    if date_obj.month == 12:
        end = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)
    
    return start.date(), end.date()

def safe_template_render(template_name: str,
                         context: Optional[Dict] = None,
                         **kwargs: Any) -> str:
    """
    Safely render a template with error handling and context sanitization.
    
    Args:
        template_name: Name of the template
        context: Template context dictionary
        **kwargs: Additional context variables
        
    Returns:
        str: Rendered template
    """
    try:
        if context is None:
            context = {}
        context.update(kwargs)
        
        # Add common context variables
        context['current_year'] = datetime.utcnow().year
        context['app_name'] = current_app.config.get('APP_NAME', 'BusinessApp')
        
        return render_template(template_name, **context)
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e))

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, handling division by zero and None values.
    
    Args:
        numerator: The numerator in the division
        denominator: The denominator in the division
        default: The default value to return if division is not possible
        
    Returns:
        float: The result of the division, or the default value if division is not possible
    """
    try:
        if denominator is None or denominator == 0:
            return default
        if numerator is None:
            return default
        return float(numerator) / float(denominator)
    except (TypeError, ValueError):
        return default

def generate_lot_number(product_id=None):
    """
    Generate a unique lot number.
    Format: LOT-YYYYMMDD-XXXX where XXXX is a random alphanumeric string.
    """
    date_str = datetime.utcnow().strftime('%Y%m%d')
    # Generate a random 6-character suffix
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    lot_number = f"LOT-{date_str}-{suffix}"

    # Ensure uniqueness (just in case)
    while InventoryLot.query.filter_by(lot_number=lot_number).first():
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        lot_number = f"LOT-{date_str}-{suffix}"
    
    return lot_number


def _get_product_image_paths() -> Dict[str, str]:
    """
    Resolve the configured upload directory and URL path for product images.
    """
    url_path = current_app.config.get('PRODUCT_IMAGE_URL_PATH', 'uploads/products')
    upload_dir = current_app.config.get('PRODUCT_IMAGE_UPLOAD_PATH')
    if not upload_dir:
        upload_dir = os.path.join(current_app.static_folder, url_path)
    os.makedirs(upload_dir, exist_ok=True)
    return {'url_path': url_path, 'upload_dir': upload_dir}


def save_product_image(file_storage, product_id: Optional[int] = None) -> Optional[str]:
    """
    Persist an uploaded product image and return its relative URL path.
    """
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError('Invalid image filename.')

    if not allowed_file(filename):
        raise ValueError('Unsupported image type.')

    ext = get_file_extension(filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    prefix = f"product_{product_id}" if product_id else "product"
    final_name = f"{prefix}_{timestamp}.{ext}"

    paths = _get_product_image_paths()
    destination = os.path.join(paths['upload_dir'], final_name)
    file_storage.save(destination)

    return f"{paths['url_path']}/{final_name}"


def delete_product_image(filename: Optional[str]):
    """
    Remove a stored product image if it is not the shared default.
    """
    if not filename:
        return

    default_image = current_app.config.get('DEFAULT_PRODUCT_IMAGE')
    if default_image and filename == default_image:
        return

    full_path = os.path.join(current_app.static_folder, filename)
    try:
        os.remove(full_path)
    except OSError:
        logger.warning("Failed to delete product image %s", full_path)

# app/utils/filters.py

from typing import Any
from datetime import datetime
from markupsafe import Markup
from markupsafe import Markup as FlaskMarkup
import locale

# Set default locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def format_currency(value, currency='KES', grouping=True):
    """
    Format a number as a currency string.
    
    Args:
        value: The numeric value to format
        currency: The currency code (default: 'KES')
        grouping: Whether to use thousands separators (default: True)
        
    Returns:
        str: Formatted currency string or empty string if value is None
    """
    if value is None:
        return ""
        
    try:
        # Convert to float first to handle string inputs
        value = float(value)
        
        # Format the number as currency
        if currency == 'KES':
            return f'KSh {value:,.2f}'
        else:
            return locale.currency(value, symbol=True, grouping=grouping, international=False)
    except (ValueError, TypeError):
        return str(value)

def format_date(value, format='%Y-%m-%d'):
    """
    Format a date or datetime object to a custom date string.
    
    Args:
        value: The date/datetime object or ISO format string to format
        format: The format string (default: '%Y-%m-%d')
        
    Returns:
        str: Formatted date string or empty string if value is None
    """
    if value is None:
        return ""
        
    if isinstance(value, str):
        try:
            # Try to parse ISO format string
            if 'T' in value or ' ' in value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00').split('T')[0])
            else:
                value = datetime.strptime(value, '%Y-%m-%d')
        except (ValueError, AttributeError):
            return value
    
    try:
        return value.strftime(format)
    except (AttributeError, ValueError):
        return str(value)

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """
    Format a datetime object or ISO format string to a custom string format.
    
    Args:
        value: The datetime object or ISO format string to format
        format: The format string (default: '%Y-%m-%d %H:%M:%S')
        
    Returns:
        str: Formatted datetime string or empty string if value is None
    """
    if value is None:
        return ""
        
    if isinstance(value, str):
        try:
            # Try to parse ISO format string
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return value
    
    try:
        return value.strftime(format)
    except (AttributeError, ValueError):
        return str(value)

def render_safe(html):
    """
    Mark HTML as safe for rendering in templates.
    
    Args:
        html: The HTML string to mark as safe
        
    Returns:
        Markup: A Markup object that won't be escaped by Jinja2
    """
    if html is None:
        return ""
    return FlaskMarkup(html)

def render_safe_data(data: Any) -> Any:
    """Prepare data for template rendering with type safety"""
    if isinstance(data, dict):
        return {key: render_safe_data(value) for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        return [render_safe_data(item) for item in data]
    elif data is None or isinstance(data, (str, int, float, bool)):
        return data
    else:
        return str(data) if hasattr(data, '__str__') else None

# Dictionary of all filters to register
filters = {
    'datetimeformat': format_datetime,
    'dateformat': format_date,
    'currency': format_currency,
    'rendersafe': render_safe,
    'rendersafedata': render_safe_data
}

# Create filter registry for compatibility
filter_registry = filters
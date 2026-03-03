from datetime import datetime
from markupsafe import Markup

def register_template_filters(app):
    """Register custom template filters."""
    def format_number(value, precision=0):
        """Format number with thousands separators and optional decimal places."""
        if value is None:
            return ''
        try:
            if isinstance(value, (int, float)):
                if precision == 0:
                    return f"{int(value):,}"
                return f"{float(value):,.{precision}f}"
            return str(value)
        except (ValueError, TypeError):
            return str(value)

    def format_currency(value, currency='$'):
        """Format a number as a currency value."""
        if value is None:
            return ''
        try:
            return f"{currency}{format_number(value, 2)}"
        except (ValueError, TypeError):
            return str(value)

    def format_date(value, format='%Y-%m-%d'):
        """Format a date object as a string."""
        if value is None:
            return ''
        try:
            if isinstance(value, str):
                # Try to parse the string as a date
                from datetime import datetime as dt
                value = dt.strptime(value, '%Y-%m-%d')
            return value.strftime(format)
        except (ValueError, AttributeError):
            return str(value)

    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        """Format a datetime object as a string."""
        return format_date(value, format)

    def render_safe(html):
        """Mark HTML as safe for rendering in templates."""
        return Markup(html) if html else ''

    def nl2br(value):
        """Convert newlines to <br> tags."""
        if value is None:
            return ''
        # Replace newlines with <br> tags and mark as safe
        return Markup(str(value).replace('\n', '<br>\n'))

    # Register all filters
    app.jinja_env.filters.update({
        'number': format_number,
        'number_format': format_number,  # Alias used by analytics templates
        'comma': format_number,  # Alias for backward compatibility
        'currency': format_currency,
        'date': format_date,
        'datetime': format_datetime,
        'datetimeformat': format_datetime,  # Alias for backward compatibility
        'safe': render_safe,
        'render_safe': render_safe,  # Alias for backward compatibility
        'nl2br': nl2br
    })

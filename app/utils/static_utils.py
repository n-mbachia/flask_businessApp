import os
import hashlib
from flask import current_app, url_for
from pathlib import Path

def get_static_asset_path(filename):
    """
    Get the versioned path for a static file with cache busting.
    In production, uses file modification time for versioning.
    In development, uses a hash of the file contents.
    """
    if not filename:
        return ''

    static_folder = current_app.static_folder
    file_path = os.path.join(static_folder, filename)
    
    if not os.path.exists(file_path):
        return url_for('static', filename=filename)

    # Get file modification time for versioning
    if current_app.config['ENV'] == 'production':
        version = int(os.path.getmtime(file_path))
    else:
        # In development, use file content hash for better cache busting
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
            version = file_hash[:8]

    # Add version as query parameter
    return f"{url_for('static', filename=filename)}?v={version}"

def get_js_bundle_path(bundle_name):
    """
    Get the path to a JavaScript bundle with cache busting.
    Looks for minified version in production, regular in development.
    """
    if current_app.config['ENV'] == 'production':
        filename = f"dist/js/{bundle_name}.min.js"
    else:
        filename = f"js/pages/{bundle_name}.js"
    
    return get_static_asset_path(filename)

def get_css_bundle_path(bundle_name):
    """
    Get the path to a CSS bundle with cache busting.
    Looks for minified version in production, regular in development.
    """
    if current_app.config['ENV'] == 'production':
        filename = f"dist/css/{bundle_name}.min.css"
    else:
        filename = f"css/{bundle_name}.css"
    
    return get_static_asset_path(filename)

def get_image_path(image_name, size=None, format='webp'):
    """
    Get the path to an image with optional size and format.
    Supports responsive images with srcset.
    """
    base_name = os.path.splitext(image_name)[0]
    
    if size:
        # For responsive images, use the sized version
        filename = f"img/{size}/{base_name}.{format}"
    else:
        filename = f"img/{base_name}.{format}"
    
    return get_static_asset_path(filename)

def setup_static_assets(app):
    """
    Set up static assets configuration.
    Creates necessary directories and performs any required setup.
    """
    static_folder = app.static_folder
    
    # Create directories if they don't exist
    directories = [
        'css/components',
        'css/lib',
        'css/pages',
        'css/themes',
        'js/components',
        'js/lib',
        'js/pages',
        'js/utils',
        'img',
        'fonts'
    ]
    
    for directory in directories:
        path = os.path.join(static_folder, directory)
        os.makedirs(path, exist_ok=True)
    
    # Add static utils to template context
    @app.context_processor
    def inject_static_utils():
        return {
            'static_file': get_static_asset_path,
            'js_bundle': get_js_bundle_path,
            'css_bundle': get_css_bundle_path,
            'image': get_image_path
        }

# Add template filters
def register_template_filters(app):
    """Register custom template filters for static files."""
    @app.template_filter('static_version')
    def static_version_filter(filename):
        return get_static_asset_path(filename)
    
    @app.template_filter('image_url')
    def image_url_filter(image_name, size=None):
        return get_image_path(image_name, size=size)

# Example usage in templates:
# {{ 'css/main.css'|static_version }}
# {{ 'logo.png'|image_url }}
# {{ 'logo.png'|image_url(size='large') }}

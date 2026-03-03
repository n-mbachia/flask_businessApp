"""
Context processors for injecting common variables into all templates.
"""
from datetime import datetime

def register_context_processors(app):
    """Register template context processors."""
    @app.context_processor
    def inject_now():
        """Inject current datetime into all templates."""
        return {'now': datetime.utcnow()}
    
    @app.context_processor
    def inject_current_year():
        """Inject current year into all templates."""
        return {'current_year': datetime.utcnow().year}
    
    @app.context_processor
    def inject_template_vars():
        """Inject common template variables."""
        return {
            'app_name': app.config.get('APP_NAME', 'BusinessApp'),
            'debug': app.debug,
            'config': app.config
        }

# app/cli/utility_commands.py
"""
Utility and diagnostic CLI commands.
"""
import click
from flask import current_app
from flask.cli import with_appcontext


def register_utility_commands(app):
    """Register utility CLI commands."""
    
    @app.cli.command('tailwind-build')
    def tailwind_build():
        """Compile the Tailwind/PostCSS stylesheet."""
        from app.assets import ensure_tailwind_built
        ensure_tailwind_built(force=True)

    @app.cli.command('verify-security-config')
    @with_appcontext
    def verify_security_config():
        """Verify security settings are properly configured."""
        issues = []
        critical = []
        
        # Check secret key
        secret_key = current_app.config.get('SECRET_KEY', '')
        if not secret_key or len(secret_key) < 32:
            critical.append("SECRET_KEY must be at least 32 characters")
        if secret_key and secret_key in ['your-super-secret-key', 'dev-secret-key', 'change-me', 'your-super-secret-key-min-32-characters-long-change-me']:
            critical.append("SECRET_KEY is using default/placeholder value")
            
        # Check session security in production
        if not current_app.debug:
            if not current_app.config.get('SESSION_COOKIE_SECURE'):
                critical.append("SESSION_COOKIE_SECURE must be True in production")
            if current_app.config.get('SESSION_COOKIE_SAMESITE') not in ['Strict', 'Lax']:
                issues.append("SESSION_COOKIE_SAMESITE should be 'Strict' or 'Lax' in production")
        
        # Check CORS
        cors_origins = current_app.config.get('CORS_ALLOWED_ORIGINS', [])
        if "*" in cors_origins:
            issues.append("CORS allows all origins (*)")
            
        # Check admin env vars are not using defaults
        admin_password = current_app.config.get('ADMIN_PASSWORD', '')
        if admin_password and len(admin_password) < 12:
            issues.append("ADMIN_PASSWORD is less than 12 characters")
        if admin_password and admin_password in ['admin', 'password', '123456']:
            critical.append("ADMIN_PASSWORD is using common weak value")
        
        # Check database in production
        if not current_app.debug:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' in db_uri.lower():
                issues.append("SQLite detected in production; PostgreSQL recommended")
        
        # Report
        if critical:
            click.echo("CRITICAL ISSUES (must fix):", err=True)
            for issue in critical:
                click.echo(f"  ✗ {issue}", err=True)
        
        if issues:
            click.echo("\nWarnings:" if not critical else "\nWarnings:")
            for issue in issues:
                click.echo(f"  ⚠ {issue}")
        
        if not critical and not issues:
            click.echo("✓ Security configuration looks good!")
            return
        
        if critical:
            raise click.Abort()

    @app.cli.command('check-db-health')
    @with_appcontext
    def check_db_health():
        """Check database connectivity and basic health."""
        from sqlalchemy import text
        from app import db
        
        try:
            result = db.session.execute(text('SELECT 1'))
            click.echo("✓ Database connection successful")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            click.echo(f"✓ Found {len(tables)} tables: {', '.join(tables[:5])}" + 
                      ("..." if len(tables) > 5 else ""))
            
        except Exception as e:
            click.echo(f"✗ Database connection failed: {e}", err=True)
            raise click.Abort()

    @app.cli.command('show-config')
    @click.option('--sensitive/--no-sensitive', default=False, help='Show sensitive values (masked by default)')
    @with_appcontext
    def show_config(sensitive):
        """Display current configuration (safe values only by default)."""
        import json
        
        safe_keys = [
            'DEBUG', 'TESTING', 'ENV', 
            'SESSION_COOKIE_SECURE', 'SESSION_COOKIE_HTTPONLY', 'SESSION_COOKIE_SAMESITE',
            'PERMANENT_SESSION_LIFETIME', 'CACHE_TYPE', 'MAIL_SERVER', 'MAIL_PORT',
            'MAIL_USE_TLS', 'MAIL_DEFAULT_SENDER', 'SALES_TAX_RATE',
            'REQUIRE_EMAIL_CONFIRMATION', 'CORS_ALLOWED_ORIGINS'
        ]
        
        config_data = {}
        for key in safe_keys:
            value = current_app.config.get(key)
            if key == 'CORS_ALLOWED_ORIGINS' and isinstance(value, list):
                config_data[key] = value
            else:
                config_data[key] = str(value) if value is not None else None
        
        if sensitive:
            click.echo("WARNING: Showing sensitive configuration values", err=True)
            sensitive_keys = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL', 'CACHE_REDIS_URL']
            for key in sensitive_keys:
                value = current_app.config.get(key, '')
                config_data[key] = value[:10] + '...[MASKED]' if value else None
        
        click.echo(json.dumps(config_data, indent=2))

# app/cli/admin_commands.py
"""
Admin user management CLI commands.
"""
import os
import re
import click
from flask import current_app
from flask.cli import with_appcontext


def validate_email(email):
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password):
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""


def get_env_admin_credentials():
    """Get admin credentials from environment variables."""
    return (
        current_app.config.get('ADMIN_USERNAME'),
        current_app.config.get('ADMIN_EMAIL'),
        current_app.config.get('ADMIN_PASSWORD')
    )


def register_admin_commands(app):
    """Register admin-related CLI commands."""
    
    @app.cli.command('create-admin')
    @click.option('--username', required=False, help='Admin username (or set ADMIN_USERNAME)')
    @click.option('--email', required=False, help='Admin email (or set ADMIN_EMAIL)')
    @click.option('--password', required=False, hide_input=True, help='Admin password (or set ADMIN_PASSWORD)')
    @click.option('--interactive/--no-interactive', default=False, help='Force interactive mode')
    @with_appcontext
    def create_admin(username, email, password, interactive):
        """
        Create or update the super-user/vendor account.
        
        Priority: CLI args > Environment variables > Interactive prompts
        """
        from app.models import User
        from app import db
        
        # Determine source of credentials
        if interactive or not all([username, email, password]):
            env_user, env_email, env_pass = get_env_admin_credentials()
            
            # Use CLI args if provided, else env, else prompt
            username = username or env_user
            email = email or env_email
            password = password or env_pass
            
            # Prompt for any missing values
            if not username:
                username = click.prompt("Admin username", type=str)
            if not email:
                email = click.prompt("Admin email", type=str)
            if not password:
                password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
        
        # Validate inputs
        if not username or len(username) < 3:
            click.echo("Error: Username must be at least 3 characters", err=True)
            raise click.Abort()
            
        if not validate_email(email):
            click.echo("Error: Invalid email format", err=True)
            raise click.Abort()
            
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            click.echo(f"Error: {error_msg}", err=True)
            raise click.Abort()

        # Database operations
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            if existing.username != username:
                click.echo(f"Error: Email {email} already registered with different username", err=True)
                raise click.Abort()
                
            # Update existing user
            existing.is_admin = True
            existing.is_vendor = True
            existing.confirmed = True
            existing.set_password(password)
            db.session.commit()
            click.echo(f'✓ Updated admin user "{username}" with vendor privileges')
            current_app.logger.info(f"Admin user {username} updated via CLI")
        else:
            # Create new user
            admin = User(
                username=username, 
                email=email, 
                is_admin=True, 
                is_vendor=True, 
                confirmed=True
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f'✓ Created admin user "{username}"')
            current_app.logger.info(f"Admin user {username} created via CLI")

    @app.cli.command('create-admin-auto')
    @with_appcontext
    def create_admin_auto():
        """
        Non-interactive admin creation using environment variables only.
        Fails if ADMIN_USERNAME, ADMIN_EMAIL, or ADMIN_PASSWORD not set.
        """
        username = current_app.config.get('ADMIN_USERNAME')
        email = current_app.config.get('ADMIN_EMAIL')
        password = current_app.config.get('ADMIN_PASSWORD')
        
        if not all([username, email, password]):
            missing = []
            if not username: missing.append("ADMIN_USERNAME")
            if not email: missing.append("ADMIN_EMAIL")
            if not password: missing.append("ADMIN_PASSWORD")
            click.echo(f"Error: Missing environment variables: {', '.join(missing)}", err=True)
            raise click.Abort()
        
        ctx = click.get_current_context()
        ctx.invoke(create_admin, username=username, email=email, password=password, interactive=False)

    @app.cli.command('reset-admin-password')
    @click.option('--username', prompt=True, help='Admin username')
    @click.option('--new-password', prompt=True, hide_input=True, confirmation_prompt=True, 
                  help='New password (12+ chars, mixed case, number, special char)')
    @with_appcontext
    def reset_admin_password(username, new_password):
        """Reset password for an existing admin user."""
        from app.models import User
        from app import db
        
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            click.echo(f"Error: {error_msg}", err=True)
            raise click.Abort()
        
        admin = User.query.filter_by(username=username, is_admin=True).first()
        if not admin:
            click.echo(f"Error: Admin user '{username}' not found", err=True)
            raise click.Abort()
        
        admin.set_password(new_password)
        db.session.commit()
        click.echo(f'✓ Password reset for admin "{username}"')
        current_app.logger.info(f"Admin password reset for {username}")

    @app.cli.command('list-admins')
    @with_appcontext
    def list_admins():
        """List all admin users."""
        from app.models import User
        
        admins = User.query.filter_by(is_admin=True).all()
        if not admins:
            click.echo("No admin users found.")
            return
        
        click.echo(f"\n{'Username':<20} {'Email':<30} {'Vendor':<10} {'Confirmed':<10}")
        click.echo("-" * 70)
        for admin in admins:
            click.echo(f"{admin.username:<20} {admin.email:<30} "
                      f"{'Yes' if admin.is_vendor else 'No':<10} "
                      f"{'Yes' if admin.confirmed else 'No':<10}")

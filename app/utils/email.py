# app/utils/email.py

from flask import current_app, render_template, url_for
from threading import Thread
from datetime import datetime

# Conditional import for flask_mail
try:
    from flask_mail import Message
    _HAS_MAIL = True
except ImportError:
    _HAS_MAIL = False
    
    class Message:
        def __init__(self, *args, **kwargs):
            pass

# Import mail after app context is available
def get_mail():
    try:
        from app import mail
        return mail
    except ImportError:
        return None

def send_async_email(app, msg):
    """Send an email asynchronously."""
    if not _HAS_MAIL:
        current_app.logger.warning("Email not configured - skipping email send")
        return
        
    with app.app_context():
        try:
            mail = get_mail()
            if mail:
                mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {str(e)}")

def send_email(subject, sender, recipients, text_body, html_body):
    """Send an email with the given parameters."""
    if not _HAS_MAIL:
        current_app.logger.warning("Email not configured - skipping email send")
        return
        
    msg = Message(
        subject=subject,
        sender=sender,
        recipients=recipients,
        body=text_body,
        html=html_body
    )
    # Send email asynchronously
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_confirmation_email(user_email, token):
    """Send an email with a confirmation link to the user."""
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    
    # Render the email template
    html = render_template(
        'email/confirm_email.html',
        user=user_email,
        confirm_url=confirm_url,
        current_year=datetime.utcnow().year
    )
    
    # Create a plain text version
    text = f"""Welcome to BusinessApp!\n\n"""
    text += f"Please confirm your email by visiting the following link:\n{confirm_url}\n\n"
    text += "If you didn't create an account, please ignore this email.\n"
    
    # Send the email
    send_email(
        subject="Confirm Your Email Address",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user_email],
        text_body=text,
        html_body=html
    )

def send_password_reset_email(email, reset_url):
    """Send a password reset email to the user."""
    html = render_template(
        'email/reset_password.html',
        reset_url=reset_url,
        current_year=datetime.utcnow().year
    )
    
    text = f"To reset your password, visit the following link:\n{reset_url}\n\n"
    text += "If you did not make this request, please ignore this email.\n"
    
    send_email(
        subject="Password Reset Request",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email],
        text_body=text,
        html_body=html
    )

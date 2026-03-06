# app/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from sqlalchemy import or_
from app import db
from datetime import datetime
from app.models import User
from app.forms.user_forms import (
    LoginForm, RegisterForm, UpdateAccountForm,
    SettingsForm, ForgotPasswordForm, ResetPasswordForm
)
from app.utils.decorators import handle_exceptions, rate_limit
from app.utils.email import send_password_reset_email, send_confirmation_email
from app.validators import (
    UserValidator, validate_entity, sanitize_input, 
    check_security, SecurityValidator
)
from app.security import SecurityUtils
from app.utils import is_safe_url
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _generate_password_reset_token(email: str) -> str:
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('PASSWORD_RESET_SALT', 'password-reset-salt')
    return serializer.dumps(email, salt=salt)


def _verify_password_reset_token(token: str) -> str | None:
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('PASSWORD_RESET_SALT', 'password-reset-salt')
    max_age = current_app.config.get('PASSWORD_RESET_EXPIRATION', 3600)
    return serializer.loads(token, salt=salt, max_age=max_age)


def _can_request_password_reset() -> bool:
    last_request = session.get('last_password_reset_request')
    if not last_request:
        return True
    try:
        previous = datetime.fromisoformat(last_request)
    except ValueError:
        return True
    cooldown = current_app.config.get('PASSWORD_RESET_COOLDOWN', 60)
    return (datetime.utcnow() - previous).total_seconds() >= cooldown


def _record_password_reset_request():
    session['last_password_reset_request'] = datetime.utcnow().isoformat()

@auth_bp.route('/register', methods=['GET', 'POST'])
@handle_exceptions
@rate_limit(max_calls=3, period=300)  # 3 registrations per 5 minutes
def register():
    """
    Register a new user with enhanced security validation.

    :param: GET/POST
    :return: rendered register.html template
    """
    form = RegisterForm()

    def _clean_validation_message(raw_message: str) -> str:
        msg = str(raw_message).strip()
        if msg.startswith('Validation failed: '):
            msg = msg[len('Validation failed: '):].strip()
        if 'Value error,' in msg:
            msg = msg.split('Value error,', 1)[1].strip()
        if ' [type=' in msg:
            msg = msg.split(' [type=', 1)[0].strip()
        return msg

    if form.validate_on_submit():
        try:
            # Validate and sanitize input data
            user_data = {
                'username': sanitize_input(form.username.data, 'html'),
                'email': sanitize_input(form.email.data, 'html'),
                'password': form.password.data
            }

            # Check for security issues
            if check_security(user_data['username'], 'all') or check_security(user_data['email'], 'all'):
                SecurityUtils.log_security_event('registration_security_issue', {
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'ip': request.remote_addr
                }, 'warning')
                form.username.errors.append('Invalid input detected.')
                return render_template('auth/register.html', form=form), 400

            # Validate with Pydantic
            validated_data, errors = validate_entity('user', user_data, sanitize=False)
            if errors:
                for error in errors:
                    raw_error = str(error)
                    message = _clean_validation_message(raw_error)
                    lowered = raw_error.lower()

                    if 'password' in lowered:
                        form.password.errors.append(message)
                    elif 'username' in lowered:
                        form.username.errors.append(message)
                    elif 'email' in lowered:
                        form.email.errors.append(message)
                    else:
                        flash(message, 'danger')
                return render_template('auth/register.html', form=form), 400

            # Check if user already exists
            if User.query.filter(or_(User.username == validated_data.username,
                                    User.email == validated_data.email)).first():
                SecurityUtils.log_security_event('duplicate_registration_attempt', {
                    'username': validated_data.username,
                    'email': validated_data.email,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Username or email already exists', 'danger')
                return render_template('auth/register.html', form=form), 400

            # Create new user
            user = User(
                username=validated_data.username,
                email=validated_data.email,
                threshold=10.0
            )
            user.set_password(validated_data.password)

            # Auto‑confirm if email confirmation is not required
            if not current_app.config.get('REQUIRE_EMAIL_CONFIRMATION', False):
                user.confirmed = True
                user.confirmed_on = datetime.utcnow()

            db.session.add(user)
            db.session.commit()

            # Send confirmation email only if required
            if current_app.config.get('REQUIRE_EMAIL_CONFIRMATION', True):
                token = user.generate_confirmation_token()
                send_confirmation_email(user.email, token)
                flash('Registration successful! Please check your email to confirm your account.', 'success')
            else:
                flash('Registration successful! You can now log in.', 'success')

            # Redirect to login page after successful registration
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register.html', form=form), 500

    return render_template('auth/register.html', form=form)

    
@auth_bp.route('/login', methods=['GET', 'POST'])
@handle_exceptions
@rate_limit(max_calls=5, period=60)
def login():
    """
    Handle user login with enhanced security.
    
    Supports both regular form submissions and AJAX requests.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            # Sanitize and validate input
            email = sanitize_input(form.email.data, 'html')
            password = form.password.data
            
            # Check for security issues
            if check_security(email, 'all'):
                SecurityUtils.log_security_event('login_security_issue', {
                    'email': email,
                    'ip': request.remote_addr
                }, 'warning')
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid input detected.'
                    }), 400
                flash('Invalid input detected.', 'danger')
                return redirect(url_for('auth.login'))
            
            user = User.query.filter_by(email=email).first()
            
            if user is None or not user.check_password(password):
                # Log failed login attempt
                SecurityUtils.log_security_event('login_failed', {
                    'email': email,
                    'user_exists': user is not None,
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent')
                }, 'warning')
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid email or password.'
                    }), 401
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Check if account is locked due to too many failed attempts
            if hasattr(user, 'is_locked') and user.is_locked():
                SecurityUtils.log_security_event('login_blocked_account_locked', {
                    'email': email,
                    'user_id': user.id,
                    'ip': request.remote_addr
                }, 'warning')
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'status': 'error',
                        'message': 'Account is temporarily locked. Please try again later.'
                    }), 403
                flash('Account is temporarily locked. Please try again later.', 'danger')
                return redirect(url_for('auth.login'))
                
            login_user(user, remember=form.remember.data)
            
            # Log successful login
            SecurityUtils.log_security_event('login_success', {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'remember_me': form.remember.data
            }, 'info')
            
            next_page = request.args.get('next')
            
            # Validate next URL to prevent open redirects
            if not is_safe_url(next_page):
                next_page = None
                
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'success',
                    'redirect': next_page or url_for('main.dashboard')
                })
                
            return redirect(next_page or url_for('main.dashboard'))
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            SecurityUtils.log_security_event('login_error', {
                'email': form.email.data,
                'error': str(e),
                'ip': request.remote_addr
            }, 'error')
            
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'error',
                    'message': 'An error occurred during login. Please try again.'
                }), 500
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
        
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'error',
            'errors': form.errors
        }), 400
        
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout a user.

    :param: GET
    :return: redirect to main.index
    """
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@handle_exceptions
def profile():
    """
    Unified profile and settings page.
    """
    profile_form = UpdateAccountForm(current_user.username, current_user.email)
    settings_form = SettingsForm()

    if request.method == 'GET':
        profile_form.username.data = current_user.username
        profile_form.email.data = current_user.email
        settings_form.process(obj=current_user)

    # Only process profile form on POST to this route
    if profile_form.validate_on_submit():
        try:
            current_user.username = sanitize_input(profile_form.username.data, 'html')
            current_user.email = sanitize_input(profile_form.email.data, 'html')
            if profile_form.new_password.data:
                current_user.set_password(profile_form.new_password.data)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}", exc_info=True)
            flash('An error occurred while updating your profile. Please try again.', 'danger')

    return render_template('auth/profile.html',
                           profile_form=profile_form,
                           settings_form=settings_form,
                           current_theme=settings_form.theme.data or current_user.theme)

@auth_bp.route('/unconfirmed')
def unconfirmed():
    """Show the unconfirmed account page."""
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth_bp.route('/resend-confirmation')
@login_required
def resend_confirmation():
    """Resend the account confirmation email."""
    if not current_app.config['REQUIRE_EMAIL_CONFIRMATION']:
        flash('Email confirmation is not required.', 'info')
        return redirect(url_for('main.index'))

    if current_user.confirmed:
        flash('Your account is already confirmed.', 'info')
        return redirect(url_for('main.index'))
    
    try:
        token = current_user.generate_confirmation_token()
        send_confirmation_email(current_user.email, token)
        flash('A new confirmation email has been sent to your email address.', 'info')
    except Exception as e:
        current_app.logger.error(f'Error resending confirmation email: {str(e)}')
        flash('An error occurred while sending the confirmation email. Please try again later.', 'error')
    
    return redirect(url_for('auth.unconfirmed'))

@auth_bp.route('/confirm/<token>')
@login_required
def confirm_email(token):
    """Confirm a user's email address."""
    if current_user.confirmed:
        flash('Account already confirmed.', 'info')
        return redirect(url_for('main.index'))
    
    if current_user.confirm(token):
        db.session.commit()
        flash('Thank you for confirming your email address!', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'error')
    
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@handle_exceptions
def forgot_password():
    """
    Handle password reset request.
    
    Sends a password reset email if the email exists in the system.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        if not _can_request_password_reset():
            flash('Please wait a bit before requesting another reset link.', 'warning')
            return redirect(url_for('auth.forgot_password'))

        email = sanitize_input(form.email.data, 'email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = _generate_password_reset_token(user.email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_password_reset_email(user.email, reset_url)
            SecurityUtils.log_security_event('password_reset_requested', {
                'user_id': user.id,
                'email': user.email,
                'ip': request.remote_addr
            }, 'info')

        _record_password_reset_request()
        flash('If an account exists with this email, you will receive a password reset link.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@handle_exceptions
def reset_password(token):
    """
    Handle password reset with token.
    
    Validates the token and allows the user to set a new password.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    # Verify token
    try:
        email = _verify_password_reset_token(token)
    except (SignatureExpired, BadSignature, ValueError):
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Update password
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been reset. Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form, token=token)

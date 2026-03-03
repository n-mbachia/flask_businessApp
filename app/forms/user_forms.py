# app/forms/user_forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, 
    BooleanField, IntegerField, SelectField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, ValidationError, Length, Regexp, Optional, NumberRange
)

class RegisterForm(FlaskForm):
    """
    Form for user registration.

    Validates the uniqueness of both the username and email.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=20),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers and underscores')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$',
            message='Password must contain uppercase, lowercase, and numbers'
        )
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        from app.models import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        from app.models import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')

class LoginForm(FlaskForm):
    """
    Form for user login.

    Validates the email and password.
    """
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    """
    Form for updating user account information.

    Validates the uniqueness of the username and email if changed.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=20),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers and underscores')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required to make changes')
    ])
    new_password = PasswordField('New Password (leave blank to keep current)', validators=[
        Optional(),
        Length(min=8, message='New password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Account')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UpdateAccountForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            from app.models import User
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            from app.models import User
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different one.')

    def validate_current_password(self, field):
        from app.models import User
        user = User.query.filter_by(username=self.original_username).first()
        if not user or not user.check_password(field.data):
            raise ValidationError('Current password is incorrect')

class ForgotPasswordForm(FlaskForm):
    """
    Form for requesting a password reset.
    """
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    """
    Form for resetting a user's password.
    """
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class SettingsForm(FlaskForm):
    # Notification Preferences
    email_notifications = BooleanField('Email Notifications')
    low_stock_alerts = BooleanField('Low Stock Alerts')
    
    # Display Settings
    items_per_page = SelectField(
        'Items Per Page',
        choices=[
            (10, '10 items'),
            (25, '25 items'),
            (50, '50 items'),
            (100, '100 items')
        ],
        coerce=int,
        validators=[NumberRange(min=10, max=100)]
    )
    
    theme = SelectField(
        'Theme',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('system', 'System Default')
        ]
    )
    
    # Business Settings
    threshold = IntegerField(
        'Low Stock Threshold',
        validators=[NumberRange(min=0)]
    )
    
    currency = SelectField(
        'Currency',
        choices=[
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
            ('KES', 'Kenyan Shilling (KSh)')
        ]
    )
    
    submit = SubmitField('Save Settings')

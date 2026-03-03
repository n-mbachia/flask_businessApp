from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, BooleanField, SelectField,
    SubmitField, validators, IntegerField
)
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
import re

class CustomerForm(FlaskForm):
    """Form for creating and updating customers."""
    
    # Basic Information
    name = StringField(
        'Full Name',
        validators=[
            DataRequired(message='Name is required'),
            Length(min=2, max=120, message='Name must be between 2 and 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'John Doe',
            'autofocus': True
        }
    )
    
    email = StringField(
        'Email',
        validators=[
            Optional(),
            Email(message='Invalid email address'),
            Length(max=120, message='Email cannot exceed 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'john@example.com',
            'type': 'email'
        }
    )
    
    phone = StringField(
        'Phone',
        validators=[
            Optional(),
            Length(min=6, max=20, message='Phone number must be between 6 and 20 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '+1 (555) 123-4567',
            'type': 'tel'
        }
    )
    
    company = StringField(
        'Company',
        validators=[
            Optional(),
            Length(max=120, message='Company name cannot exceed 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Acme Inc.'
        }
    )
    
    # Address Information
    address = StringField(
        'Address',
        validators=[
            Optional(),
            Length(max=255, message='Address cannot exceed 255 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '123 Main St'
        }
    )
    
    address2 = StringField(
        'Address Line 2',
        validators=[
            Optional(),
            Length(max=255, message='Address line 2 cannot exceed 255 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Apt, suite, etc. (optional)'
        }
    )
    
    city = StringField(
        'City',
        validators=[
            Optional(),
            Length(max=100, message='City name cannot exceed 100 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'New York'
        }
    )
    
    state = StringField(
        'State/Province',
        validators=[
            Optional(),
            Length(max=100, message='State/Province cannot exceed 100 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'NY'
        }
    )
    
    postal_code = StringField(
        'Postal/ZIP Code',
        validators=[
            Optional(),
            Length(max=20, message='Postal code cannot exceed 20 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '10001'
        }
    )
    
    country = StringField(
        'Country',
        validators=[
            Optional(),
            Length(max=100, message='Country name cannot exceed 100 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'United States'
        }
    )
    
    # Additional Information
    tax_id = StringField(
        'Tax/VAT ID',
        validators=[
            Optional(),
            Length(max=50, message='Tax ID cannot exceed 50 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '12-3456789'
        }
    )
    
    is_active = BooleanField(
        'Active',
        default=True,
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    notes = TextAreaField(
        'Notes',
        validators=[
            Optional(),
            Length(max=1000, message='Notes cannot exceed 1000 characters')
        ],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Any additional notes about this customer...'
        }
    )
    
    # Form actions
    submit = SubmitField(
        'Save Customer',
        render_kw={
            'class': 'btn btn-primary'
        }
    )
    
    cancel = SubmitField(
        'Cancel',
        render_kw={
            'class': 'btn btn-secondary',
            'formnovalidate': True
        }
    )
    
    def validate_phone(self, field):
        """Custom validation for phone number format."""
        if field.data:
            # Remove all non-digit characters except +, (, ), and -
            phone = re.sub(r'[^0-9+()\- ]', '', field.data)
            if not re.match(r'^[\d\s\-+\(\)]{6,20}$', phone):
                raise ValidationError('Invalid phone number format')
    
    def validate_email(self, field):
        """Ensure email is unique if provided."""
        from app.models.customer import Customer
        if field.data:
            existing_customer = Customer.query.filter_by(email=field.data.lower()).first()
            if existing_customer:
                # If editing, only error if it's a different customer
                if hasattr(self, 'customer_id'):
                    if existing_customer.id != self.customer_id:
                        raise ValidationError('Email already in use by another customer')
                # If creating, always error if email exists
                else:
                    raise ValidationError('Email address is already in use')
    
    def populate_obj(self, obj):
        """Populate the object with form data."""
        super().populate_obj(obj)
        # Ensure email is stored in lowercase
        if obj.email:
            obj.email = obj.email.lower().strip()
        # Clean phone number
        if obj.phone:
            obj.phone = re.sub(r'[^0-9+()\- ]', '', obj.phone).strip()
            
    @classmethod
    def from_model(cls, customer):
        """Create form from an existing customer model."""
        form = cls()
        form.customer_id = customer.id
        form.name.data = customer.name
        form.email.data = customer.email
        form.phone.data = customer.phone
        form.company.data = customer.company
        form.address.data = customer.address
        form.address2.data = customer.address2
        form.city.data = customer.city
        form.state.data = customer.state
        form.postal_code.data = customer.postal_code
        form.country.data = customer.country
        form.tax_id.data = customer.tax_id
        form.is_active.data = customer.is_active
        form.notes.data = customer.notes
        return form

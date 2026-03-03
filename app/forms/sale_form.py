# app/forms/sale_form.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, TextAreaField, SelectField, DateField, SubmitField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange, ValidationError
)
from datetime import datetime, date
from flask import current_app

class SalesForm(FlaskForm):
    """
    Form for creating and editing sales records.
    
    Fields:
        product_id: The product being sold (required)
        date: The date of the sale (required)
        units_sold: Number of units sold (required, minimum 1)
        customer_name: Name of the customer (optional)
        notes: Additional notes about the sale (optional)
    """
    
    def __init__(self, *args, user_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        # Dynamically set product choices based on user's products
        if user_id:
            from app.models import Product
            products = Product.query.filter_by(user_id=user_id).order_by(Product.name).all()
            self.product_id.choices = [(p.id, p.name) for p in products]
    
    product_id = SelectField(
        'Product',
        validators=[DataRequired()],
        coerce=int,
        choices=[]
    )
    
    date = DateField(
        'Sale Month',
        validators=[DataRequired()],
        format=['%Y-%m', '%Y-%m-%d'],  # Accept both formats
        render_kw={"placeholder": "YYYY-MM"}
    )
    
    units_sold = IntegerField(
        'Units Sold',
        validators=[
            DataRequired(), 
            NumberRange(min=1, message='Must be at least 1')
        ],
        default=1
    )
    
    customer_name = StringField(
        'Customer Name',
        validators=[
            Optional(),
            Length(max=100, message='Customer name cannot exceed 100 characters')
        ]
    )
    
    notes = TextAreaField(
        'Notes',
        validators=[
            Optional(),
            Length(max=500, message='Notes cannot exceed 500 characters')
        ],
        render_kw={"rows": 3}
    )
    
    submit = SubmitField('Save Sale')
    
    def validate_date(self, field):
        """Validate that the date is not in the future."""
        if field.data:
            # Convert to first day of month for comparison
            first_day = date(field.data.year, field.data.month, 1)
            if first_day > date.today():
                raise ValidationError('Sale date cannot be in the future.')
    
    def validate_units_sold(self, field):
        """Validate that units sold is within available inventory."""
        if field.data and hasattr(self, 'product_id') and self.product_id.data:
            from app.models import Product, InventoryLot
            product = Product.query.get(self.product_id.data)
            if product:
                # Calculate available inventory
                available = product.current_stock or 0
                if field.data > available:
                    raise ValidationError(f'Not enough inventory. Only {available} units available.')


'''
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from app.models import Product

class SalesForm(FlaskForm):
    month = StringField("Month (YYYY-MM)", validators=[DataRequired()])
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    units_sold = IntegerField("Units Sold", validators=[DataRequired(), NumberRange(min=0)])
    total_revenue = DecimalField("Total Revenue", places=2, validators=[DataRequired()])
    customer_count = IntegerField("Customer Count", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save")

    def set_choices(self, products):
        """Populate product dropdown dynamically."""
        self.product_id.choices = [(p.id, p.name) for p in products]
'''
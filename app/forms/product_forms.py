# app/forms/product_forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField,
    FloatField, SelectField, IntegerField
)
from wtforms.validators import (
    DataRequired, NumberRange, Optional,
    ValidationError, Length
)

class ProductForm(FlaskForm):
    """
    Form for creating or updating a product.
    Used for both creation (with initial_quantity) and updates (initial_quantity ignored).
    """
    name = StringField('Product Name', validators=[
        DataRequired(),
        Length(max=100, message='Name must be less than 100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description too long')
    ])
    sku = StringField('SKU', validators=[
        Optional(),
        Length(max=50, message='SKU must be less than 50 characters')
    ])
    barcode = StringField('Barcode', validators=[
        Optional(),
        Length(max=50, message='Barcode must be less than 50 characters')
    ])
    category = SelectField('Category', choices=[
        ('Electronics', 'Electronics'),
        ('Clothing', 'Clothing'),
        ('Books', 'Books'),
        ('Home & Garden', 'Home & Garden'),
        ('Sports & Outdoors', 'Sports & Outdoors'),
        ('Beauty & Personal Care', 'Beauty & Personal Care'),
        ('Food & Beverages', 'Food & Beverages'),
        ('Automotive', 'Automotive'),
        ('Toys & Games', 'Toys & Games'),
        ('Uncategorized', 'Uncategorized')
    ], default='Uncategorized')
    cogs_per_unit = FloatField('COGS per Unit', validators=[
        DataRequired(),
        NumberRange(min=0, message='COGS must be positive')
    ])
    selling_price_per_unit = FloatField('Selling Price per Unit', validators=[
        DataRequired(),
        NumberRange(min=0, message='Price must be positive')
    ])
    reorder_level = IntegerField('Reorder Level', validators=[
        Optional(),
        NumberRange(min=0, message='Reorder level must be positive')
    ], default=10)
    initial_quantity = IntegerField('Initial Quantity', validators=[
        Optional(),
        NumberRange(min=0, message='Quantity must be positive')
    ], default=0)
    submit = SubmitField('Save')

    def validate_selling_price_per_unit(self, field):
        if self.cogs_per_unit.data is not None and field.data <= self.cogs_per_unit.data:
            raise ValidationError('Selling price must be greater than COGS')

    def validate_cogs_per_unit(self, field):
        if self.selling_price_per_unit.data is not None and field.data >= self.selling_price_per_unit.data:
            raise ValidationError('COGS must be less than selling price')


class ProductEditForm(FlaskForm):
    """
    Form for editing an existing product via the edit modal.
    All fields are optional to allow partial updates.
    """
    name = StringField('Product Name', validators=[
        Optional(),
        Length(max=100)
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])
    sku = StringField('SKU', validators=[
        Optional(),
        Length(max=50)
    ])
    barcode = StringField('Barcode', validators=[
        Optional(),
        Length(max=50)
    ])
    category = SelectField('Category', choices=[
        ('Electronics', 'Electronics'),
        ('Clothing', 'Clothing'),
        ('Books', 'Books'),
        ('Home & Garden', 'Home & Garden'),
        ('Sports & Outdoors', 'Sports & Outdoors'),
        ('Beauty & Personal Care', 'Beauty & Personal Care'),
        ('Food & Beverages', 'Food & Beverages'),
        ('Automotive', 'Automotive'),
        ('Toys & Games', 'Toys & Games'),
        ('Uncategorized', 'Uncategorized')
    ], default='Uncategorized')
    cogs_per_unit = FloatField('COGS per Unit', validators=[
        Optional(),
        NumberRange(min=0)
    ])
    selling_price_per_unit = FloatField('Selling Price per Unit', validators=[
        Optional(),
        NumberRange(min=0)
    ])
    reorder_level = IntegerField('Reorder Level', validators=[
        Optional(),
        NumberRange(min=0)
    ], default=10)
    submit = SubmitField('Update')

    def validate_selling_price_per_unit(self, field):
        # Only validate if both fields are provided
        if (self.cogs_per_unit.data is not None and field.data is not None and
                field.data <= self.cogs_per_unit.data):
            raise ValidationError('Selling price must be greater than COGS')

    def validate_cogs_per_unit(self, field):
        if (self.selling_price_per_unit.data is not None and field.data is not None and
                field.data >= self.selling_price_per_unit.data):
            raise ValidationError('COGS must be less than selling price')

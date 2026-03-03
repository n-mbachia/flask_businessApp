# app/forms/inventory_lot_form.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, 
    FloatField, SelectField, IntegerField,
    DateField
)
from wtforms.validators import (
    DataRequired, NumberRange,
    ValidationError, Optional, Length
)
from flask import current_app

class InventoryLotForm(FlaskForm):
    """
    Form for creating or updating an inventory lot record.

    Fields:
        product_id (SelectField): Select a product associated with the inventory lot.
        lot_number (StringField): Unique identifier for the inventory lot, max length 50 characters.
        received_date (DateField): Date when the inventory was received, in 'YYYY-MM-DD' format.
        quantity_received (IntegerField): Number of items received, must be at least 1.
        cost_per_unit (FloatField): Cost of each item received, must be positive.
        expiration_date (DateField): Optional expiration date of the items, in 'YYYY-MM-DD' format.
        submit (SubmitField): Submit the form to save the inventory lot.

    Methods:
        validate_lot_number(field): Ensures the lot number is unique.
        validate_expiration_date(field): Checks that expiration date is not before the received date.
    """

    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    lot_number = StringField('Lot Number', validators=[
        Optional(),  # allow empty
        Length(max=50)
    ])
    received_date = DateField('Received Date', format='%Y-%m-%d', validators=[DataRequired()])
    quantity_received = IntegerField('Quantity Received', validators=[
        DataRequired(),
        NumberRange(min=1, message='Quantity must be at least 1')
    ])
    cost_per_unit = FloatField('Cost per Unit', validators=[
        DataRequired(),
        NumberRange(min=0, message='Cost must be positive')
    ])
    expiration_date = DateField('Expiration Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Lot')

    def validate_lot_number(self, field):
        from app.models import InventoryLot
        lot = InventoryLot.query.filter_by(lot_number=field.data).first()
        if lot:
            raise ValidationError('This lot number already exists. Please use a different one.')

    def validate_expiration_date(self, field):
        if field.data and field.data < self.received_date.data:
            raise ValidationError('Expiration date cannot be before received date')

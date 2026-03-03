from flask_wtf import FlaskForm
from wtforms import (
    SelectField, IntegerField, 
    FloatField, TextAreaField, SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Optional

class InventoryMovementForm(FlaskForm):
    """
    Form for creating inventory movement records.
    
    Fields:
        movement_type: Type of inventory movement (receipt, sale, etc.)
        quantity: Number of items for this movement
        unit_cost: Cost per unit (optional)
        notes: Additional information about the movement
    """
    movement_type = SelectField('Movement Type', choices=[
        ('receipt', 'Stock Receipt'),
        ('sale', 'Sale'),
        ('adjustment_in', 'Adjustment (In)'),
        ('adjustment_out', 'Adjustment (Out)'),
        ('return', 'Return'),
        ('damage', 'Damage')
    ], validators=[DataRequired()])
    
    quantity = IntegerField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=1, message='Quantity must be at least 1')
    ])
    
    unit_cost = FloatField('Unit Cost', validators=[
        Optional(),
        NumberRange(min=0, message='Cost must be positive')
    ])
    
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Update Stock')
    
    def validate_quantity(self, field):
        """Ensure quantity is positive for all movement types"""
        if field.data <= 0:
            raise ValidationError('Quantity must be greater than 0')

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, FloatField, 
    SelectField, BooleanField, DateField
)
from wtforms.validators import (
    DataRequired, NumberRange, Optional as OptionalValidator,
    Regexp, Length, ValidationError
)
from flask import current_app, request

from app.models.costs import CostTypeEnum, CostClassification

class CostForm(FlaskForm):
    """
    Form for creating or updating a cost entry with enhanced type safety.
    
    Fields:
        date: Date when the cost was incurred
        amount: Monetary amount of the cost
        cost_type: Type of cost from the CostTypeEnum
        classification: Whether the cost is fixed, variable, or semi-variable
        is_direct: Whether this is a direct cost (directly attributable to a product)
        is_tax_deductible: Whether this cost is tax deductible
        product_id: Optional product this cost is associated with
        description: Optional description of the cost
        is_recurring: Whether this is a recurring cost
        recurrence_frequency: How often the cost recurs (if recurring)
        submit: Submit button
    """
    
    date = DateField(
        'Date',
        validators=[DataRequired()],
        default=datetime.utcnow,
        format='%Y-%m-%d'
    )
    
    amount = FloatField(
        'Amount',
        validators=[
            DataRequired(),
            NumberRange(min=0, message='Amount must be positive')
        ],
        render_kw={"step": "0.01", "min": "0"}
    )
    
    cost_type = SelectField(
        'Category',
        choices=[(t.value, t.value.replace('_', ' ').title()) for t in CostTypeEnum],
        validators=[DataRequired()]
    )
    
    classification = SelectField(
        'Cost Type',
        choices=[
            (CostClassification.FIXED.value, 'Fixed Cost'),
            (CostClassification.VARIABLE.value, 'Variable Cost'),
            (CostClassification.SEMI_VARIABLE.value, 'Semi-Variable Cost')
        ],
        validators=[DataRequired()]
    )
    
    '''is_direct = BooleanField(
        'Direct Cost?',
        default=False,
        description="Is this cost directly attributable to a product?"
    )'''
    
    is_direct = BooleanField('Is Direct', render_kw={
        'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
        'x_ref': 'isDirect',
        '@change': "$refs.productField.style.display = $event.target.checked ? 'block' : 'none'"
    })

    is_tax_deductible = BooleanField(
        'Tax Deductible?',
        default=True,
        description="Can this cost be deducted from taxable income?"
    )
    
    product_id = SelectField(
        'Product',
        coerce=lambda x: int(x) if x else None,
        validators=[OptionalValidator()],
        choices=[],
        render_kw={"class": "select2"}
    )
    
    description = StringField(
        'Description',
        validators=[
            OptionalValidator(),
            Length(max=200, message='Description cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "Optional description of the cost"}
    )
    
    is_recurring = BooleanField(
        'Recurring Cost?',
        default=False,
        description="Does this cost recur on a regular basis?",
        render_kw={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            '@change': "$refs.recurrenceField.style.display = $event.target.checked ? 'block' : 'none'"
        }
    )

    '''is_recurring = BooleanField(
        'Recurring Cost?',
        default=False,
        description="Does this cost recur on a regular basis?"
    )'''
    
    recurrence_frequency = SelectField(
        'Recurrence',
        choices=[
            ('', 'Not Recurring'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly')
        ],
        validators=[OptionalValidator()],
        default=''
    )
    
    submit = SubmitField('Save Cost')
    
    def __init__(self, user_id: Optional[int] = None, **kwargs: Any) -> None:
        """Initialize the form with dynamic product choices."""
        super().__init__(**kwargs)
        self.user_id = user_id
        if user_id is not None:
            self.set_product_choices(user_id)
        
        # Set default classification based on cost_type if not provided
        if self.cost_type.data and not self.classification.data:
            self._set_default_classification()
    
    def _set_default_classification(self) -> None:
        """Set default classification based on cost type."""
        try:
            cost_type = CostTypeEnum(self.cost_type.data)
            self.classification.data = CostClassification.from_cost_type(cost_type).value
        except (KeyError, ValueError):
            self.classification.data = CostClassification.FIXED.value
    
    def validate_recurrence_frequency(self, field: SelectField) -> None:
        """Validate that recurrence frequency is provided if is_recurring is True."""
        if self.is_recurring.data and not field.data:
            raise ValidationError('Please select a recurrence frequency for recurring costs')
    
    def set_product_choices(self, user_id: int) -> None:
        """Set the product choices for the product_id field."""
        from app.models import Product
        try:
            products = Product.query.filter_by(user_id=user_id).order_by(Product.name).all()
            self.product_id.choices = [(p.id, p.name) for p in products]
            # Set a default empty choice if no products exist
            if not self.product_id.choices:
                self.product_id.choices = [('', 'No products available')]
                self.product_id.render_kw = {'disabled': True}
        except Exception as e:
            current_app.logger.error(f"Error setting product choices: {e}")
            self.product_id.choices = []
    
    def populate_obj(self, obj: Any) -> None:
        """
        Populate the given object with form data.
        
        Args:
            obj: The object to populate with form data
        """
        super().populate_obj(obj)
        
        # Convert string values to enum instances
        if hasattr(obj, 'cost_type') and self.cost_type.data:
            obj.cost_type = CostTypeEnum(self.cost_type.data)
        if hasattr(obj, 'classification') and self.classification.data:
            obj.classification = CostClassification(self.classification.data)
        
        # Clear product_id if not a direct cost
        if hasattr(obj, 'product_id') and not self.is_direct.data:
            obj.product_id = None
        
        # Clear recurrence_frequency if not recurring
        if hasattr(obj, 'recurrence_frequency') and not self.is_recurring.data:
            obj.recurrence_frequency = None


__all__ = ['CostForm']

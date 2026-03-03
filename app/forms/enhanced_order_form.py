"""
Enhanced Order Form - Improved UX with dynamic item management,
real-time validation, and better user experience.
"""

from flask_wtf import FlaskForm
from wtforms import (
    SelectField, TextAreaField, StringField, DecimalField, IntegerField,
    BooleanField, FieldList, FormField, HiddenField, SubmitField, 
    Form as NoCsrfForm
)
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError, Length
from datetime import datetime
from decimal import Decimal
from flask import current_app


class OrderItemForm(NoCsrfForm):
    """Enhanced subform for individual order items with better validation."""
    product_id = SelectField(
        'Product', 
        coerce=int, 
        validators=[DataRequired(message='Please select a product')],
        render_kw={
            'class': 'form-select product-select',
            'hx-get': '/api/v1/enhanced_orders/product/',
            'hx-target': '.product-details',
            'hx-trigger': 'change'
        }
    )
    quantity = IntegerField(
        'Quantity', 
        validators=[
            DataRequired(message='Quantity is required'),
            NumberRange(min=1, message='Quantity must be at least 1')
        ], 
        default=1,
        render_kw={
            'class': 'form-control quantity-input',
            'min': '1',
            'hx-post': '/api/v1/enhanced_orders/calculate-item-subtotal',
            'hx-target': '.item-subtotal',
            'hx-trigger': 'change, keyup delay:500ms'
        }
    )
    unit_price = DecimalField(
        'Unit Price', 
        places=2, 
        validators=[
            DataRequired(message='Unit price is required'),
            NumberRange(min=0, message='Price cannot be negative')
        ],
        render_kw={
            'class': 'form-control price-input',
            'step': '0.01',
            'min': '0',
            'hx-post': '/api/v1/enhanced_orders/calculate-item-subtotal',
            'hx-target': '.item-subtotal',
            'hx-trigger': 'change, keyup delay:500ms'
        }
    )
    subtotal = DecimalField(
        'Subtotal', 
        places=2, 
        validators=[
            DataRequired(message='Subtotal is required'),
            NumberRange(min=0, message='Subtotal cannot be negative')
        ],
        render_kw={
            'class': 'form-control item-subtotal',
            'readonly': True,
            'style': 'background-color: #f8f9fa;'
        }
    )
    notes = StringField(
        'Notes',
        validators=[
            Optional(),
            Length(max=200, message='Notes cannot exceed 200 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Optional notes for this item...'
        }
    )
    
    # Hidden fields for AJAX operations
    product_name = HiddenField()
    product_sku = HiddenField()
    product_stock = HiddenField()
    
    def validate_quantity(self, field):
        """Enhanced quantity validation."""
        if field.data <= 0:
            raise ValidationError('Quantity must be greater than 0')
        
        # Check if quantity exceeds available stock
        if hasattr(self, 'product_stock') and self.product_stock.data:
            try:
                available_stock = int(self.product_stock.data)
                if field.data > available_stock:
                    raise ValidationError(f'Only {available_stock} units available in stock')
            except (ValueError, TypeError):
                pass
    
    def validate_unit_price(self, field):
        """Enhanced unit price validation."""
        if field.data < 0:
            raise ValidationError('Unit price cannot be negative')
        
        # Check if price is reasonable (not too high or too low)
        if field.data > 999999:
            raise ValidationError('Unit price seems too high')
        
        if field.data > 0 and field.data < 0.01:
            raise ValidationError('Unit price must be at least $0.01')


class CustomerQuickAddForm(NoCsrfForm):
    """Quick customer addition form for order creation."""
    name = StringField(
        'Customer Name',
        validators=[
            Optional(),
            Length(min=2, max=120, message='Name must be between 2 and 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Enter customer name...'
        }
    )
    email = StringField(
        'Email',
        validators=[
            Optional(),
            Length(max=120, message='Email cannot exceed 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'type': 'email',
            'placeholder': 'customer@example.com'
        }
    )
    phone = StringField(
        'Phone',
        validators=[
            Optional(),
            Length(max=20, message='Phone cannot exceed 20 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '+1 (555) 123-4567'
        }
    )
    company = StringField(
        'Company',
        validators=[
            Optional(),
            Length(max=120, message='Company cannot exceed 120 characters')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Company name (optional)'
        }
    )


class EnhancedOrderForm(FlaskForm):
    """Enhanced order form with improved UX and validation."""
    
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        self._set_customer_choices()
        self._set_product_choices()
        self._initialize_form_elements()
    
    def _initialize_form_elements(self):
        """Initialize dynamic form elements."""
        # Add initial empty item if none exist
        if len(self.items.entries) == 0:
            self.items.append_entry()
    
    def populate_from_order(self, order):
        """Populate form with existing order data including items."""
        if not order:
            return
        
        # Set basic fields
        if hasattr(order, 'customer_id') and order.customer_id:
            self.customer_id.data = order.customer_id
        if hasattr(order, 'order_date') and order.order_date:
            self.order_date.data = order.order_date
        if hasattr(order, 'payment_status') and order.payment_status:
            self.payment_status.data = order.payment_status
        if hasattr(order, 'payment_method') and order.payment_method:
            self.payment_method.data = order.payment_method
        if hasattr(order, 'notes') and order.notes:
            self.notes.data = order.notes
        if hasattr(order, 'status') and order.status:
            self.status.data = order.status
        
        # Clear existing items and populate from order
        self.items.entries = []
        if hasattr(order, 'items') and order.items:
            for item in order.items:
                item_form = OrderItemForm()
                item_form.product_id.data = item.product_id
                item_form.quantity.data = item.quantity
                item_form.unit_price.data = item.unit_price
                if hasattr(item, 'notes'):
                    item_form.notes.data = item.notes
                self.items.append_entry(item_form)
        
        # Ensure we have at least one empty item for new additions
        if len(self.items.entries) == 0:
            self.items.append_entry()
    
    def _set_customer_choices(self):
        """Set customer choices with recent customers first."""
        if not self.user_id:
            self.customer_id.choices = [(0, 'Walk-in / Guest')]
            return
        
        try:
            from app.services.customer_service import CustomerService
            
            # Get recent customers
            recent_customers = CustomerService.get_recent_customers(self.user_id, limit=5)
            
            choices = [(0, 'Walk-in / Guest')]
            
            # Add recent customers
            if recent_customers:
                choices.append((-1, '--- Recent Customers ---'))
                for customer in recent_customers:
                    display_name = customer.name
                    if customer.company:
                        display_name += f' ({customer.company})'
                    choices.append((customer.id, display_name))
            
            # Add all active customers
            from app.models import Customer
            all_customers = Customer.query.filter_by(
                user_id=self.user_id, is_active=True
            ).order_by(Customer.name).all()
            
            if all_customers:
                choices.append((-2, '--- All Customers ---'))
                for customer in all_customers:
                    display_name = customer.name
                    if customer.company:
                        display_name += f' ({customer.company})'
                    choices.append((customer.id, display_name))
            
            self.customer_id.choices = choices
            
        except Exception:
            # Fallback to basic choices
            self.customer_id.choices = [(0, 'Walk-in / Guest')]
    
    def _set_product_choices(self):
        """Set product choices with stock information."""
        try:
            from app.models import Product
            products = Product.query.filter_by(
                user_id=self.user_id, is_active=True
            ).order_by(Product.name).all()
            
            choices = [(0, 'Select Product')]
            for product in products:
                stock_info = f" (Stock: {product.quantity_available})"
                price_info = f" - ${product.selling_price_per_unit:.2f}" if product.selling_price_per_unit else ""
                display_name = f"{product.name}{stock_info}{price_info}"
                choices.append((product.id, display_name))
            
            # Update choices for all item forms
            for item in self.items:
                item.product_id.choices = choices
                
        except Exception:
            # Fallback to basic choices
            choices = [(0, 'Select Product')]
            for item in self.items:
                item.product_id.choices = choices
    
    # Customer Information
    customer_id = SelectField(
        'Customer',
        coerce=int,
        validators=[Optional()],
        render_kw={
            'class': 'form-select customer-select',
            'hx-get': '/api/v1/customers/search',
            'hx-target': '#customer-search-results',
            'hx-trigger': 'keyup delay:300ms'
        }
    )
    
    # Quick customer addition
    quick_add_customer = BooleanField(
        'Add New Customer',
        default=False,
        render_kw={
            'class': 'form-check-input',
            'hx-target': '#quick-customer-form',
            'hx-swap': 'innerHTML'
        }
    )
    
    quick_customer = FormField(CustomerQuickAddForm)
    
    # Order Information
    order_date = StringField(
        'Order Date',
        validators=[DataRequired(message='Order date is required')],
        default=datetime.utcnow().strftime('%Y-%m-%d'),
        render_kw={
            'class': 'form-control',
            'type': 'date',
            'max': datetime.utcnow().strftime('%Y-%m-%d')
        }
    )
    
    status = SelectField(
        'Status',
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending',
        render_kw={
            'class': 'form-select status-select',
            'hx-post': '/api/v1/enhanced_orders/status-change',
            'hx-target': '#status-warning'
        }
    )
    
    payment_status = SelectField(
        'Payment Status',
        choices=[
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded')
        ],
        default='unpaid',
        render_kw={
            'class': 'form-select'
        }
    )
    
    payment_method = SelectField(
        'Payment Method',
        choices=[
            ('', 'Select Payment Method'),
            ('cash', 'Cash'),
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('check', 'Check'),
            ('other', 'Other')
        ],
        validators=[Optional()],
        render_kw={
            'class': 'form-select'
        }
    )
    
    # Order Items with enhanced management
    items = FieldList(
        FormField(OrderItemForm),
        min_entries=1,
        max_entries=50,
        render_kw={
            'class': 'order-items-container'
        }
    )
    
    # Order Totals with real-time calculation
    subtotal = DecimalField(
        'Subtotal',
        places=2,
        default=0.00,
        render_kw={
            'class': 'form-control fw-bold',
            'readonly': True,
            'style': 'background-color: #f8f9fa;'
        }
    )
    
    tax_rate = DecimalField(
        'Tax Rate %',
        places=2,
        default=16.0,
        validators=[
            NumberRange(min=0, max=100, message='Tax rate must be between 0 and 100')
        ],
        render_kw={
            'class': 'form-control tax-rate-input',
            'hx-post': '/api/v1/enhanced_orders/calculate-totals',
            'hx-trigger': 'change, keyup delay:500ms',
            'hx-target': '#order-totals'
        }
    )
    
    tax_amount = DecimalField(
        'Tax Amount',
        places=2,
        default=0.00,
        render_kw={
            'class': 'form-control',
            'readonly': True,
            'style': 'background-color: #f8f9fa;'
        }
    )
    
    shipping_amount = DecimalField(
        'Shipping',
        places=2,
        default=0.00,
        validators=[
            NumberRange(min=0, message='Shipping cannot be negative')
        ],
        render_kw={
            'class': 'form-control shipping-input',
            'hx-post': '/api/v1/enhanced_orders/calculate-totals',
            'hx-trigger': 'change, keyup delay:500ms',
            'hx-target': '#order-totals'
        }
    )
    
    discount_amount = DecimalField(
        'Discount',
        places=2,
        default=0.00,
        validators=[
            NumberRange(min=0, message='Discount cannot be negative')
        ],
        render_kw={
            'class': 'form-control discount-input',
            'hx-post': '/api/v1/enhanced_orders/calculate-totals',
            'hx-trigger': 'change, keyup delay:500ms',
            'hx-target': '#order-totals'
        }
    )
    
    total_amount = DecimalField(
        'Total',
        places=2,
        default=0.00,
        render_kw={
            'class': 'form-control fw-bold fs-5',
            'readonly': True,
            'style': 'background-color: #e3f2fd; border: 2px solid #2196f3;'
        }
    )
    
    # Additional Options
    is_recurring = BooleanField(
        'Recurring Order',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    mark_completed = BooleanField(
        'Mark as Completed (Update Inventory)',
        default=True,
        render_kw={
            'class': 'form-check-input',
            'hx-target': '#inventory-warning',
            'hx-trigger': 'change'
        }
    )
    
    update_inventory = BooleanField(
        'Update Inventory Now',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    notes = TextAreaField(
        'Order Notes',
        validators=[
            Optional(),
            Length(max=1000, message='Notes cannot exceed 1000 characters')
        ],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special instructions or notes about this order...',
            'hx-post': '/api/v1/enhanced_orders/validate-notes',
            'hx-target': '#notes-warning',
            'hx-trigger': 'keyup delay:1000ms'
        }
    )
    
    # Form actions
    submit = SubmitField(
        'Create Order',
        render_kw={
            'class': 'btn btn-primary btn-lg',
            'hx-disabled-elt': 'this',
            'hx-indicator': '.htmx-indicator'
        }
    )
    
    save_draft = SubmitField(
        'Save as Draft',
        render_kw={
            'class': 'btn btn-outline-secondary',
            'formnovalidate': True
        }
    )
    
    cancel = SubmitField(
        'Cancel',
        render_kw={
            'class': 'btn btn-danger',
            'formnovalidate': True,
            'onclick': 'return confirm("Are you sure you want to cancel? All changes will be lost.");'
        }
    )
    
    # Hidden fields for dynamic operations
    add_item = HiddenField('Add Item')
    remove_item = HiddenField('Remove Item')
    form_token = HiddenField()
    
    def validate_items(self, field):
        """Enhanced items validation."""
        if not field.entries or not any(item.data.get('product_id') for item in field.entries):
            raise ValidationError('At least one order item is required')
        
        # Validate each item
        for i, item in enumerate(field.entries, 1):
            if item.data.get('product_id'):
                if not item.data.get('quantity') or item.data.get('quantity') <= 0:
                    raise ValidationError(f'Item {i}: Quantity must be greater than 0')
                
                if not item.data.get('unit_price') or item.data.get('unit_price') < 0:
                    raise ValidationError(f'Item {i}: Unit price must be greater than or equal to 0')
    
    def validate_customer_id(self, field):
        """Enhanced customer validation."""
        if field.data in (-1, -2):
            raise ValidationError('Please select a valid customer')

        # Allow walk-in/guest orders (no customer selected).
        if field.data in (0, None, ''):
            return

        if field.data <= 0:
            raise ValidationError('Please select a valid customer')
        
        elif field.data > 0:
            # Validate customer exists and is active
            from app.models import Customer
            customer = Customer.query.filter_by(
                id=field.data, 
                user_id=self.user_id, 
                is_active=True
            ).first()
            if not customer:
                raise ValidationError('Selected customer is not available')

    def validate(self, extra_validators=None):
        """Custom validation with conditional quick-customer requirements."""
        is_valid = super().validate(extra_validators=extra_validators)

        if self.quick_add_customer.data:
            name = (self.quick_customer.name.data or '').strip()
            if not name:
                self.quick_customer.name.errors.append(
                    'Customer name is required when adding a new customer'
                )
                is_valid = False

        return is_valid
    
    def calculate_totals(self):
        """Calculate order totals with enhanced validation."""
        subtotal = Decimal('0')
        valid_items = 0
        
        for item in self.items:
            if item.data.get('product_id'):
                quantity = Decimal(str(item.data.get('quantity', 0)))
                unit_price = Decimal(str(item.data.get('unit_price', 0)))
                item_subtotal = quantity * unit_price
                
                # Update item subtotal
                item.subtotal.data = item_subtotal
                subtotal += item_subtotal
                valid_items += 1
        
        if valid_items == 0:
            return {
                'subtotal': Decimal('0'),
                'tax_amount': Decimal('0'),
                'shipping_amount': Decimal('0'),
                'discount_amount': Decimal('0'),
                'total': Decimal('0'),
                'valid_items': 0
            }
        
        # Calculate tax and totals
        tax_rate = Decimal(str(self.tax_rate.data or 0)) / 100
        tax_amount = subtotal * tax_rate
        shipping = Decimal(str(self.shipping_amount.data or 0))
        discount = Decimal(str(self.discount_amount.data or 0))
        
        total = (subtotal + tax_amount + shipping) - discount
        
        # Update form fields
        self.subtotal.data = subtotal
        self.tax_amount.data = tax_amount
        self.total_amount.data = max(Decimal('0'), total)
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'shipping_amount': shipping,
            'discount_amount': discount,
            'total': max(Decimal('0'), total),
            'valid_items': valid_items
        }
    
    def get_order_data(self):
        """Extract order data from form."""
        return {
            'customer_id': self.customer_id.data if self.customer_id.data > 0 else None,
            'order_date': self.order_date.data,
            'status': self.status.data,
            'payment_status': self.payment_status.data,
            'payment_method': self.payment_method.data,
            'is_recurring': self.is_recurring.data,
            'notes': self.notes.data,
            'total_amount': self.total_amount.data
        }
    
    def get_items_data(self):
        """Extract items data from form."""
        items_data = []
        for item in self.items:
            if item.data.get('product_id'):
                items_data.append({
                    'product_id': item.product_id.data,
                    'quantity': item.quantity.data,
                    'unit_price': float(item.unit_price.data),
                    'notes': item.notes.data
                })
        return items_data
    
    def get_quick_customer_data(self):
        """Extract quick customer data if enabled."""
        if self.quick_add_customer.data:
            return {
                'name': self.quick_customer.name.data,
                'email': self.quick_customer.email.data,
                'phone': self.quick_customer.phone.data,
                'company': self.quick_customer.company.data
            }
        return None

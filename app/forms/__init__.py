"""
Forms Package

This package contains all form classes for the application.
It provides a centralized way to import forms used across the application.
"""

# Import forms from individual modules
from .user_forms import RegisterForm, LoginForm, UpdateAccountForm      
from .product_forms import ProductForm
from .sale_form import SalesForm
from .inventory_lot_form import InventoryLotForm
from .inventory_movement_form import InventoryMovementForm
from .cost_form import CostForm

# Export forms for easier imports
__all__ = [
    'LoginForm', 'RegisterForm', 'UpdateAccountForm', 'ProductForm', 'SalesForm',
    'InventoryLotForm', 'InventoryMovementForm', 'CostForm'
]
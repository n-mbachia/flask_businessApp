"""
Services package for business logic and data processing.

This package contains various service modules that handle the core business logic,
data processing, and analytics for the application.
"""

# Import key classes and functions to make them available at package level
from .profit_calculator import ProfitCalculator
from .trend_services import get_trends_analysis
from .dashboard_metrics import DashboardMetrics
from .lot_analytics import LotAnalytics
from .performance_analyzer import PerformanceAnalyzer, performance_analyzer
from .sales_updater import SalesUpdater  
from .inventory_service import InventoryService

# Import new services
try:
    from .order_service import OrderService
    _HAS_ORDER_SERVICE = True
except ImportError:
    OrderService = None
    _HAS_ORDER_SERVICE = False

try:
    from .customer_service import CustomerService
    _HAS_CUSTOMER_SERVICE = True
except ImportError:
    CustomerService = None
    _HAS_CUSTOMER_SERVICE = False

# Define __all__ for explicit exports
__all__ = [
    'ProfitCalculator',
    'get_trends_analysis',
    'DashboardMetrics',
    'LotAnalytics',
    'PerformanceAnalyzer',
    'SalesUpdater',
    'performance_analyzer',
    'InventoryService',
    'OrderService',
    'CustomerService'
]
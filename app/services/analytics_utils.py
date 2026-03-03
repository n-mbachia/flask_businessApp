"""
Analytics Utilities Module

This module provides core analytics functionality including error handling,
caching, and base classes for product analytics operations.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypeVar, Callable, Type, Union, Tuple
from functools import wraps
import logging
import time

from sqlalchemy import func, and_, exc, or_, text
from sqlalchemy.orm import Query
from flask import current_app

from app import db
from app.models import Product, CostEntry
from app.utils.cache import cached, get_cache

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AnalyticsError(Exception):
    """Base exception for analytics-related errors."""
    def __init__(self, message: str, status_code: int = 500, payload: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for API responses."""
        rv = dict(self.payload or {})
        rv['message'] = self.message
        rv['status'] = 'error'
        rv['code'] = self.status_code
        return rv


class ValidationError(AnalyticsError):
    """Exception raised for validation errors."""
    def __init__(self, message: str, payload: Optional[Dict] = None):
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(AnalyticsError):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str, payload: Optional[Dict] = None):
        super().__init__(message, status_code=404, payload=payload)


class AnalyticsBase:
    """Base class for analytics operations with common functionality."""
    CACHE_TIMEOUT = 3600  # 1 hour cache timeout
    MAX_QUERY_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    @classmethod
    def _retry_query(
        cls,
        query_func: Callable[[], T],
        error_context: Optional[Dict[str, Any]] = None,
        retries: int = None
    ) -> T:
        """
        Execute a query with retry logic for transient errors.
        
        Args:
            query_func: Function that executes the query
            error_context: Additional context for error logging
            retries: Number of retry attempts remaining
            
        Returns:
            The query result
            
        Raises:
            AnalyticsError: If all retry attempts fail
        """
        retries = retries or cls.MAX_QUERY_RETRIES
        last_exception = None
        
        for attempt in range(retries):
            try:
                return query_func()
            except (exc.OperationalError, exc.InternalError) as e:
                last_exception = e
                logger.warning(
                    f"Database error (attempt {attempt + 1}/{retries}): {str(e)}",
                    extra=error_context
                )
                if attempt < retries - 1:
                    time.sleep(cls.RETRY_DELAY * (attempt + 1))
        
        error_msg = "Maximum retry attempts reached for database operation"
        logger.error(error_msg, extra=error_context)
        raise AnalyticsError(
            "A database error occurred. Please try again later.",
            status_code=500,
            payload=error_context
        ) from last_exception

    @classmethod
    def _get_sales_data(
        cls,
        product_id: int,
        month: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get sales data for a product in a specific month from the analytics view.
        
        Args:
            product_id: ID of the product
            month: Month in 'YYYY-MM' format
            context: Context dictionary for error handling
            
        Returns:
            Dictionary containing sales data
        """
        try:
            year, month_num = map(int, month.split('-'))
            
            query = text("""
                SELECT 
                    COALESCE(SUM(total_revenue), 0) as revenue,
                    COALESCE(SUM(units_sold), 0) as units_sold,
                    COALESCE(SUM(total_cogs), 0) as cogs
                FROM product_sales_view
                WHERE product_id = :product_id
                AND user_id = :user_id
                AND EXTRACT(YEAR FROM order_date) = :year
                AND EXTRACT(MONTH FROM order_date) = :month
                AND status = 'completed'
            """)
            
            result = db.session.execute(query, {
                'product_id': product_id,
                'user_id': context.get('user_id'),
                'year': year,
                'month': month_num
            }).fetchone()
            
            return {
                'revenue': float(result[0]) if result and result[0] is not None else 0.0,
                'units_sold': int(result[1]) if result and result[1] is not None else 0,
                'cogs': float(result[2]) if result and result[2] is not None else 0.0
            }
            
        except Exception as e:
            error_msg = f"Error fetching sales data: {str(e)}"
            logger.error(error_msg, extra=context)
            return {
                'revenue': 0.0,
                'units_sold': 0,
                'cogs': 0.0
            }


class ProductAnalytics(AnalyticsBase):
    """
    Provides analytics for product-related metrics including profitability calculations,
    sales analysis, and performance metrics.
    """
    
    @classmethod
    @cached(timeout=AnalyticsBase.CACHE_TIMEOUT, key_prefix="product_profitability")
    def calculate_product_profitability(
        cls,
        product_id: int,
        month: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate profitability metrics for a specific product and month.
        
        Args:
            product_id: ID of the product to analyze
            month: Month in 'YYYY-MM' format
            user_id: Optional user ID for access control
            
        Returns:
            Dictionary containing profitability metrics
            
        Raises:
            AnalyticsError: If the product is not found or calculation fails
        """
        error_context = {
            'product_id': product_id,
            'month': month,
            'user_id': user_id,
            'function': 'calculate_product_profitability'
        }
        
        try:
            # Get product with validation
            product = cls._get_product(product_id, user_id)
            
            # Get sales data from analytics view
            sales_data = cls._get_sales_data(product_id, month, error_context)
            
            # Get shared costs
            shared_costs = cls._get_shared_costs(month, product.user_id, error_context)
            
            # Get total revenue for allocation
            total_revenue = cls._get_total_revenue(month, product.user_id, error_context) or 1.0
            
            # Calculate allocation ratios and costs
            allocation_ratio = sales_data['revenue'] / total_revenue if total_revenue else 0
            allocated_costs = shared_costs * allocation_ratio
            
            # Get direct costs
            direct_costs = cls._get_direct_costs(product_id, month, error_context)
            
            # Calculate final metrics
            total_costs = sales_data['cogs'] + allocated_costs + direct_costs
            net_profit = sales_data['revenue'] - total_costs
            threshold = cls._calculate_margin_threshold(product)
            
            return {
                'revenue': sales_data['revenue'],
                'cogs': sales_data['cogs'],
                'gross_profit': sales_data['revenue'] - sales_data['cogs'],
                'gross_margin': ((sales_data['revenue'] - sales_data['cogs']) / sales_data['revenue'] * 100) if sales_data['revenue'] else 0,
                'net_profit': net_profit,
                'net_margin': (net_profit / sales_data['revenue'] * 100) if sales_data['revenue'] else 0,
                'allocation_ratio': allocation_ratio,
                'allocated_costs': allocated_costs,
                'direct_costs': direct_costs,
                'alert': (net_profit / sales_data['revenue'] * 100 < threshold) if sales_data['revenue'] else True,
                'threshold': threshold,
                'month': month,
                'product_id': product_id,
                'calculated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.exception(
                "Error in product profitability calculation",
                extra=error_context
            )
            if not isinstance(e, AnalyticsError):
                raise AnalyticsError(
                    "Failed to calculate product profitability",
                    status_code=500,
                    payload=error_context
                ) from e
            raise
    
    @classmethod
    def _get_product(cls, product_id: int, user_id: Optional[int] = None) -> Product:
        """Get a product with optional user validation."""
        query = Product.query
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        product = query.get(product_id)
        
        if not product:
            raise AnalyticsError(
                f"Product {product_id} not found" + 
                (f" for user {user_id}" if user_id else ""),
                status_code=404
            )
        return product
    
    @classmethod
    def _get_shared_costs(
        cls,
        month: str,
        user_id: int,
        context: Dict[str, Any]
    ) -> float:
        """Get shared costs for a specific month and user."""
        try:
            query = text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM cost_entries
                WHERE month = :month
                AND product_id IS NULL
                AND user_id = :user_id
            """)
            
            result = db.session.execute(query, {
                'month': month,
                'user_id': user_id
            }).scalar()
            
            return float(result) if result is not None else 0.0
            
        except Exception as e:
            logger.error(
                f"Error fetching shared costs: {str(e)}",
                extra=context
            )
            return 0.0
    
    @classmethod
    def _get_total_revenue(
        cls,
        month: str,
        user_id: int,
        context: Dict[str, Any]
    ) -> float:
        """Get total revenue for a specific month and user."""
        try:
            year, month_num = map(int, month.split('-'))
            
            query = text("""
                SELECT COALESCE(SUM(total_revenue), 0)
                FROM product_sales_view
                WHERE user_id = :user_id
                AND EXTRACT(YEAR FROM order_date) = :year
                AND EXTRACT(MONTH FROM order_date) = :month
                AND status = 'completed'
            """)
            
            result = db.session.execute(query, {
                'user_id': user_id,
                'year': year,
                'month': month_num
            }).scalar()
            
            return float(result) if result is not None else 1.0  # Return 1.0 to avoid division by zero
            
        except Exception as e:
            logger.error(
                f"Error fetching total revenue: {str(e)}",
                extra=context
            )
            return 1.0  # Return 1.0 to avoid division by zero
    
    @classmethod
    def _get_direct_costs(
        cls,
        product_id: int,
        month: str,
        context: Dict[str, Any]
    ) -> float:
        """Get direct costs for a specific product and month."""
        try:
            query = text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM cost_entries
                WHERE product_id = :product_id
                AND month = :month
            """)
            
            result = db.session.execute(query, {
                'product_id': product_id,
                'month': month
            }).scalar()
            
            return float(result) if result is not None else 0.0
            
        except Exception as e:
            logger.error(
                f"Error fetching direct costs: {str(e)}",
                extra=context
            )
            return 0.0
    
    @staticmethod
    def _calculate_margin_threshold(product: Product) -> float:
        """Calculate the minimum acceptable margin threshold for a product."""
        # Base threshold can be customized based on business rules
        base_threshold = 20.0  # 20% minimum margin
        
        # Adjust threshold based on product category or other factors
        if hasattr(product, 'average_monthly_volume') and product.average_monthly_volume < 10:
            return base_threshold + 10.0
            
        return base_threshold


def safe_template_render(data: Any) -> Dict[str, Any]:
    """
    Safely prepare data for template rendering by converting non-serializable types.
    
    Args:
        data: The data to prepare for rendering
        
    Returns:
        A dictionary with serializable data
    """
    if data is None:
        return {}
        
    if isinstance(data, dict):
        return {k: safe_template_render(v) for k, v in data.items()}
        
    if isinstance(data, (list, tuple)):
        return [safe_template_render(item) for item in data]
        
    if isinstance(data, (int, float, str, bool)):
        return data
        
    if hasattr(data, 'to_dict') and callable(getattr(data, 'to_dict')):
        return safe_template_render(data.to_dict())
        
    if hasattr(data, '__dict__'):
        return safe_template_render(data.__dict__)
        
    return str(data)

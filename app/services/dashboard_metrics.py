"""
Dashboard Metrics Module

This module provides functionality for calculating and retrieving metrics
for the dashboard, including sales performance, inventory status, and
product analytics.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict, Tuple, Literal, Union
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy import func, and_, or_, case, select, desc, extract, text
from sqlalchemy.orm import joinedload
from flask import current_app
from flask_login import current_user
import logging

from app import db
from app.models import Product, CostEntry, User, Sales, OrderItem, Order
from .analytics_utils import AnalyticsBase, AnalyticsError
from app.utils.cache import cached
from app.utils.helpers import format_currency, safe_divide

logger = logging.getLogger(__name__)

# Type aliases
DateRange = Tuple[datetime, datetime]
MetricValue = Union[int, float, str, bool, None]


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    total_revenue: float = 0.0
    total_orders: int = 0
    avg_order_value: float = 0.0
    top_performers: List[Dict[str, Any]] = None
    recent_sales: List[Dict[str, Any]] = None
    inventory_status: Dict[str, int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary."""
        return {
            'total_revenue': format_currency(self.total_revenue),
            'total_orders': self.total_orders,
            'avg_order_value': format_currency(self.avg_order_value),
            'top_performers': self.top_performers or [],
            'recent_sales': self.recent_sales or [],
            'inventory_status': self.inventory_status or {}
        }


class DashboardMetrics(AnalyticsBase):
    """
    Provides methods for calculating and retrieving dashboard metrics
    including sales performance, inventory status, and product analytics.
    """
    
    @staticmethod
    def calculate_margin_threshold(product: 'Product') -> float:
        """
        Calculate the minimum acceptable margin threshold for a product.
        
        Args:
            product: The Product instance to calculate the threshold for
            
        Returns:
            float: The calculated margin threshold percentage
        """
        try:
            # Use product-specific threshold if set
            if product.margin_threshold is not None:
                return product.margin_threshold
                
            # Fallback to user-specific threshold
            if hasattr(product, 'user') and product.user and product.user.default_margin_threshold is not None:
                return product.user.default_margin_threshold
                
            # Final fallback to application config or default
            return current_app.config.get('DEFAULT_MARGIN_THRESHOLD', 30.0)
        except Exception as e:
            logger.error(f"Error calculating margin threshold: {str(e)}", exc_info=True)
            return 30.0  # Safe default

    def __init__(self, user_id: Optional[int] = None):
        """
        Initialize DashboardMetrics.
        
        Args:
            user_id: Optional user ID to scope the metrics to a specific user
        """
        self.user_id = user_id or (current_user.id if current_user and hasattr(current_user, 'id') else None)
        if not self.user_id:
            raise AnalyticsError("User ID is required for dashboard metrics", status_code=400)

    @classmethod
    def get_comprehensive_metrics(cls, user_id: int) -> Dict[str, Any]:
        """Return a minimal comprehensive metrics payload for dashboards."""
        try:
            metrics = cls(user_id).get_performance_metrics()
            return {
                'kpi': metrics.to_dict(),
                'charts': {},
                'alerts': []
            }
        except Exception as e:
            logger.error("Error getting comprehensive metrics: %s", str(e), exc_info=True)
            return {
                'kpi': {},
                'charts': {},
                'alerts': []
            }
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get comprehensive performance metrics for the dashboard.
        
        Returns:
            PerformanceMetrics: Object containing all performance metrics
            
        Raises:
            AnalyticsError: If metrics calculation fails
        """
        try:
            # Define date range for metrics calculation
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)  # Last 30 days
            
            # Calculate core metrics
            total_revenue = self._calculate_total_revenue(start_date, end_date)
            total_orders = self._calculate_total_orders(start_date, end_date)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
            
            # Get additional metrics
            top_performers = self._get_top_performing_products(start_date, end_date, limit=5)
            recent_sales = self._get_recent_sales(limit=10)
            inventory_status = self._get_inventory_status()
            
            return PerformanceMetrics(
                total_revenue=total_revenue,
                total_orders=total_orders,
                avg_order_value=avg_order_value,
                top_performers=top_performers,
                recent_sales=recent_sales,
                inventory_status=inventory_status
            )
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics for user {self.user_id}: {str(e)}")
            raise AnalyticsError(f"Failed to calculate performance metrics: {str(e)}")
    
    def _calculate_total_revenue(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total revenue for the given date range."""
        try:
            query = text("""
                SELECT COALESCE(SUM(total_revenue), 0)
                FROM daily_sales_view
                WHERE user_id = :user_id
                AND sale_date BETWEEN :start_date AND :end_date
            """)
            
            result = db.session.execute(query, {
                'user_id': self.user_id,
                'start_date': start_date,
                'end_date': end_date
            }).scalar()
            
            return float(result) if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating total revenue: {str(e)}")
            return 0.0
    
    def _calculate_total_orders(self, start_date: datetime, end_date: datetime) -> int:
        """Calculate total orders for the given date range."""
        try:
            query = text("""
                SELECT COALESCE(SUM(order_count), 0)
                FROM daily_sales_view
                WHERE user_id = :user_id
                AND sale_date BETWEEN :start_date AND :end_date
            """)
            
            result = db.session.execute(query, {
                'user_id': self.user_id,
                'start_date': start_date,
                'end_date': end_date
            }).scalar()
            
            return int(result) if result else 0
            
        except Exception as e:
            logger.error(f"Error calculating total orders: {str(e)}")
            return 0
    
    @cached(timeout=3600, key_prefix=lambda self, month: f"dashboard_monthly_metrics:{self.user_id}:{month}")
    def _get_monthly_metrics(self, month: str) -> Dict[str, Any]:
        """
        Get monthly sales metrics using the analytics views.
        
        Args:
            month: Month in 'YYYY-MM' format
            
        Returns:
            Dictionary containing revenue, profit, and other metrics
        """
        try:
            # Extract year and month
            year, month_num = map(int, month.split('-'))
            
            # Query the monthly_sales_view
            query = text("""
                SELECT 
                    COALESCE(SUM(total_revenue), 0) as revenue,
                    COALESCE(SUM(total_revenue - total_cogs), 0) as profit,
                    COUNT(DISTINCT order_id) as order_count,
                    COUNT(DISTINCT customer_id) as customer_count
                FROM monthly_sales_view
                WHERE user_id = :user_id
                AND year = :year
                AND month = :month
            """)
            
            result = db.session.execute(query, {
                'user_id': self.user_id,
                'year': year,
                'month': month_num
            }).fetchone()
            
            if not result:
                return {
                    'revenue': 0.0,
                    'profit': 0.0,
                    'order_count': 0,
                    'customer_count': 0,
                    'avg_order_value': 0.0
                }
                
            revenue = float(result[0]) if result[0] else 0.0
            profit = float(result[1]) if result[1] else 0.0
            order_count = int(result[2]) if result[2] else 0
            customer_count = int(result[3]) if result[3] else 0
            
            return {
                'revenue': revenue,
                'profit': profit,
                'order_count': order_count,
                'customer_count': customer_count,
                'avg_order_value': revenue / order_count if order_count > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting monthly metrics: {str(e)}")
            raise AnalyticsError(f"Failed to get monthly metrics: {str(e)}")

    def _get_order_count(self, month: str) -> int:
        """
        Get the number of orders for a given month using the analytics views.
        
        Args:
            month: Month in 'YYYY-MM' format
            
        Returns:
            int: Number of orders for the month
        """
        try:
            year, month_num = map(int, month.split('-'))
            
            query = text("""
                SELECT COALESCE(COUNT(DISTINCT order_id), 0)
                FROM monthly_sales_view
                WHERE user_id = :user_id
                AND year = :year
                AND month = :month
            """)
            
            result = db.session.execute(query, {
                'user_id': self.user_id,
                'year': year,
                'month': month_num
            }).scalar()
            
            return int(result) if result else 0
            
        except Exception as e:
            logger.error(f"Error getting order count for {month}: {str(e)}")
            return 0
    
    @cached(timeout=3600, key_prefix=lambda self, limit=5: f"dashboard_top_performers:{self.user_id}:{limit}")
    def _get_top_performing_products(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top performing products by revenue using the analytics views.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            List of dictionaries with product performance data
        """
        try:
            query = text("""
                WITH product_performance AS (
                    SELECT 
                        psv.product_id,
                        SUM(psv.total_revenue) as total_revenue,
                        SUM(psv.total_units_sold) as total_units_sold
                    FROM product_sales_view psv
                    JOIN products p ON psv.product_id = p.id
                    WHERE psv.user_id = :user_id
                    GROUP BY psv.product_id
                )
                SELECT 
                    p.id,
                    p.name,
                    p.category,
                    COALESCE(pp.total_revenue, 0) as revenue,
                    COALESCE(pp.total_units_sold, 0) as units_sold,
                    CASE 
                        WHEN COALESCE(pp.total_units_sold, 0) > 0 
                        THEN COALESCE(pp.total_revenue, 0) / pp.total_units_sold 
                        ELSE 0 
                    END as avg_price
                FROM products p
                LEFT JOIN product_performance pp ON p.id = pp.product_id
                WHERE p.user_id = :user_id
                ORDER BY revenue DESC NULLS LAST
                LIMIT :limit
            """)
            
            results = db.session.execute(query, {
                'user_id': self.user_id,
                'limit': limit
            }).fetchall()
            
            return [{
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'revenue': float(row[3]) if row[3] else 0.0,
                'units_sold': int(row[4]) if row[4] else 0,
                'avg_price': float(row[5]) if row[5] else 0.0
            } for row in results]
            
        except Exception as e:
            logger.error(f"Error getting top performing products: {str(e)}")
            raise AnalyticsError(f"Failed to get top performing products: {str(e)}")

    @cached(timeout=1800, key_prefix=lambda self, limit=5: f"dashboard_recent_sales:{self.user_id}:{limit}")
    def _get_recent_sales(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent sales using the analytics views.
        
        Args:
            limit: Maximum number of sales to return
            
        Returns:
            List of dictionaries with recent sales data
        """
        try:
            query = text("""
                SELECT 
                    o.id as order_id,
                    o.order_date,
                    o.total_amount,
                    c.name as customer_name,
                    COUNT(DISTINCT oi.product_id) as item_count
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = :user_id
                AND o.status = 'completed'
                GROUP BY o.id, c.name, o.order_date, o.total_amount
                ORDER BY o.order_date DESC
                LIMIT :limit
            """)
            
            results = db.session.execute(query, {
                'user_id': self.user_id,
                'limit': limit
            }).fetchall()
            
            return [{
                'id': row[0],
                'date': row[1].strftime('%Y-%m-%d %H:%M:%S'),
                'amount': float(row[2]) if row[2] else 0.0,
                'customer': row[3],
                'item_count': row[4]
            } for row in results]
            
        except Exception as e:
            logger.error(f"Error getting recent sales: {str(e)}")
            return []
    
    def _get_inventory_status(self) -> Dict[str, int]:
        """Get inventory status summary."""
        try:
            # Get current stock levels
            stock_subquery = db.session.query(
                InventoryLot.product_id,
                func.sum(InventoryLot.quantity_received).label('current_stock')
            ).group_by(InventoryLot.product_id).subquery()
            
            # Get inventory status counts
            status = self._retry_query(
                lambda: db.session.query(
                    func.count(Product.id).label('total_products'),
                    func.sum(
                        case(
                            (
                                and_(
                                    stock_subquery.c.current_stock > 0,
                                    stock_subquery.c.current_stock <= Product.reorder_level
                                ),
                                1
                            ),
                            else_=0
                        )
                    ).label('low_stock'),
                    func.sum(
                        case(
                            (
                                func.coalesce(stock_subquery.c.current_stock, 0) <= 0,
                                1
                            ),
                            else_=0
                        )
                    ).label('out_of_stock'),
                    func.sum(
                        case(
                            (
                                stock_subquery.c.current_stock > Product.reorder_level,
                                1
                            ),
                            else_=0
                        )
                    ).label('in_stock')
                ).outerjoin(
                    stock_subquery,
                    Product.id == stock_subquery.c.product_id
                ).filter(
                    Product.user_id == self.user_id
                ).first(),
                error_context={
                    'function': '_get_inventory_status',
                    'user_id': self.user_id
                }
            )
            
            if not status:
                return {
                    'total_products': 0,
                    'low_stock': 0,
                    'out_of_stock': 0,
                    'in_stock': 0
                }
                
            return {
                'total_products': status.total_products or 0,
                'low_stock': status.low_stock or 0,
                'out_of_stock': status.out_of_stock or 0,
                'in_stock': status.in_stock or 0
            }
            
        except Exception as e:
            logger.exception("Error getting inventory status")
            return {
                'total_products': 0,
                'low_stock': 0,
                'out_of_stock': 0,
                'in_stock': 0
            }

    def calculate_revenue(self, product: Product) -> float:
        """
        Calculate total revenue for a product using the analytics views.
        
        Args:
            product: The Product instance
            
        Returns:
            float: Total revenue for the product
        """
        try:
            query = text("""
                SELECT COALESCE(SUM(total_revenue), 0)
                FROM product_sales_view
                WHERE product_id = :product_id
                AND user_id = :user_id
            """)
            
            result = db.session.execute(query, {
                'product_id': product.id,
                'user_id': self.user_id
            }).scalar()
            
            return float(result) if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating revenue for product {product.id}: {str(e)}")
            return 0.0

    def calculate_revenue_growth(self, product: Product, days: int = 30) -> float:
        """
        Calculate revenue growth percentage for a product over a period using the analytics views.
        
        Args:
            product: The Product instance
            days: Number of days to look back for comparison
            
        Returns:
            float: Revenue growth percentage
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get current period revenue
            current_revenue = db.session.query(
                func.coalesce(func.sum(OrderItem.subtotal), 0.0)
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                OrderItem.product_id == product.id,
                Order.user_id == self.user_id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).scalar() or 0.0
            
            # Get previous period revenue
            prev_start_date = start_date - timedelta(days=days)
            prev_revenue = db.session.query(
                func.coalesce(func.sum(OrderItem.subtotal), 0.0)
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                OrderItem.product_id == product.id,
                Order.user_id == self.user_id,
                Order.status == 'completed',
                Order.order_date >= prev_start_date,
                Order.order_date < start_date
            ).scalar() or 0.0
            
            # Calculate growth percentage
            if prev_revenue == 0:
                return float('inf') if current_revenue > 0 else 0.0
                
            return ((current_revenue - prev_revenue) / prev_revenue) * 100
            
        except Exception as e:
            logger.error(f"Error calculating revenue growth for product {product.id}: {str(e)}")
            return 0.0

    def calculate_profit_growth(self, product: Product, days: int = 30) -> float:
        """
        Calculate profit growth percentage for a product over a period.
        
        Args:
            product: The Product instance
            days: Number of days to look back for comparison
            
        Returns:
            float: Profit growth percentage
        """
        from datetime import datetime, timedelta
        
        try:
            end_date = datetime.utcnow()
            mid_date = end_date - timedelta(days=days)
            start_date = end_date - timedelta(days=days * 2)
            
            # Calculate current period profit
            current_profit = self.calculate_net_profit(product)
            
            # Calculate previous period profit
            previous_profit = db.session.query(
                func.sum(Sales.units_sold * (Product.selling_price_per_unit - Product.cogs_per_unit))
            ).join(
                Product, Product.id == Sales.product_id
            ).filter(
                Sales.product_id == product.id,
                Product.user_id == self.user_id,
                Sales.created_at >= start_date,
                Sales.created_at < mid_date
            ).scalar() or 0.0
            
            return safe_divide(current_profit - previous_profit, previous_profit) * 100 if previous_profit > 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating profit growth for product {product.id}: {str(e)}")
            return 0.0

    def calculate_margin_growth(self, product: Product, days: int = 30) -> float:
        """
        Calculate margin growth percentage for a product over a period.
        
        Args:
            product: The Product instance
            days: Number of days to look back for comparison
            
        Returns:
            float: Margin growth percentage
        """
        try:
            current_margin = self.calculate_net_margin(product)
            
            # Calculate previous period margin
            from datetime import datetime, timedelta
            end_date = datetime.utcnow() - timedelta(days=days)
            start_date = end_date - timedelta(days=days)
            
            previous_data = db.session.query(
                func.sum(Sales.units_sold * Product.selling_price_per_unit).label('revenue'),
                func.sum(Sales.units_sold * Product.cogs_per_unit).label('cogs')
            ).join(Product).filter(
                Sales.product_id == product.id,
                Product.user_id == self.user_id,
                Sales.created_at >= start_date,
                Sales.created_at < end_date
            ).first()
            
            if previous_data and previous_data.revenue and previous_data.revenue > 0:
                previous_margin = ((previous_data.revenue - previous_data.cogs) / previous_data.revenue) * 100
                return current_margin - previous_margin
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating margin growth for product {product.id}: {str(e)}")
            return 0.0

    def calculate_units_sold(self, product: Product, days: int = 30) -> int:
        """
        Calculate total units sold for a product using the analytics views.
        
        Args:
            product: The Product instance
            days: Number of days to look back
            
        Returns:
            int: Total units sold
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            result = db.session.query(
                func.coalesce(func.sum(OrderItem.quantity), 0)
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                OrderItem.product_id == product.id,
                Order.user_id == self.user_id,
                Order.status == 'completed',
                Order.order_date >= start_date,
                Order.order_date <= end_date
            ).scalar()
            
            return int(result) if result else 0
            
        except Exception as e:
            logger.error(f"Error calculating units sold for product {product.id}: {str(e)}")
            return 0

    def calculate_units_growth(self, product: Product, days: int = 30) -> float:
        """
        Calculate units sold growth percentage for a product over a period.
        
        Args:
            product: The Product instance
            days: Number of days to look back for comparison
            
        Returns:
            float: Units growth percentage
        """
        try:
            current_units = self.calculate_units_sold(product, days)
            
            # Calculate previous period units
            from datetime import datetime, timedelta
            end_date = datetime.utcnow() - timedelta(days=days)
            start_date = end_date - timedelta(days=days)
            
            previous_units = db.session.query(
                func.sum(Sales.units_sold)
            ).join(
                Product, Product.id == Sales.product_id
            ).filter(
                Sales.product_id == product.id,
                Product.user_id == self.user_id,
                Sales.created_at >= start_date,
                Sales.created_at < end_date
            ).scalar() or 0
            
            return safe_divide((current_units - previous_units), previous_units) * 100 if previous_units > 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating units growth for product {product.id}: {str(e)}")
            return 0.0

    def calculate_cogs(self, product: Product) -> float:
        """
        Calculate cost of goods sold for a product using the analytics views.
        
        Args:
            product: The Product instance
            
        Returns:
            float: Total cost of goods sold
        """
        try:
            query = text("""
                SELECT COALESCE(SUM(total_cogs), 0)
                FROM product_sales_view
                WHERE product_id = :product_id
                AND user_id = :user_id
            """)
            
            result = db.session.execute(query, {
                'product_id': product.id,
                'user_id': self.user_id
            }).scalar()
            
            return float(result) if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating COGS for product {product.id}: {str(e)}")
            return 0.0

    def calculate_net_profit(self, product: Product) -> float:
        """
        Calculate net profit for a product.
        
        Args:
            product: The Product instance
            
        Returns:
            float: Net profit for the product
        """
        revenue = self.calculate_revenue(product)
        cogs = self.calculate_cogs(product)
        return revenue - cogs

    def calculate_net_margin(self, product: Product) -> float:
        """
        Calculate net profit margin for a product.
        
        Args:
            product: The Product instance
            
        Returns:
            float: Net profit margin percentage
        """
        revenue = self.calculate_revenue(product)
        if revenue == 0:
            return 0.0
            
        net_profit = self.calculate_net_profit(product)
        return (net_profit / revenue) * 100

    def get_revenue_profit_trends(self, product_id: int, months: int = 6) -> Dict[str, Any]:
        """
        Get revenue and profit trends for a product over time.
        
        Args:
            product_id: ID of the product
            months: Number of months of data to return
            
        Returns:
            dict: Contains dates, revenue, and profit data
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func, extract, and_
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)
        
        # SQLite compatible date grouping
        monthly_data = db.session.query(
            extract('year', Sales.created_at).label('year'),
            extract('month', Sales.created_at).label('month'),
            func.sum(Sales.units_sold * Product.selling_price_per_unit).label('revenue'),
            func.sum(Sales.units_sold * (Product.selling_price_per_unit - Product.cogs_per_unit)).label('profit'),
            func.sum(Sales.units_sold).label('units')
        ).join(Product).filter(
            Sales.product_id == product_id,
            Sales.created_at.between(start_date, end_date),
            Product.user_id == self.user_id
        ).group_by(
            extract('year', Sales.created_at),
            extract('month', Sales.created_at)
        ).order_by(
            extract('year', Sales.created_at),
            extract('month', Sales.created_at)
        ).all()
        
        # Format data for chart
        dates = []
        revenue_data = []
        profit_data = []
        units_data = []
        
        for data in monthly_data:
            # Format as 'YYYY-MM'
            date_str = f"{int(data.year)}-{int(data.month):02d}"
            dates.append(date_str)
            revenue_data.append(float(data.revenue or 0))
            profit_data.append(float(data.profit or 0))
            units_data.append(int(data.units or 0))

        return {
            'dates': dates,
            'revenue': revenue_data,
            'profit': profit_data,
            'units': units_data
        }

    def get_cost_breakdown(self, product_id: int) -> dict:
        """
        Get cost breakdown for a product by cost type.
        
        Args:
            product_id: ID of the product
            
        Returns:
            dict: Contains cost types and amounts
        """
        from app.models import CostEntry
        
        results = db.session.query(
            CostEntry.cost_type,
            func.sum(CostEntry.amount).label('total_amount')
        ).filter(
            CostEntry.product_id == product_id,
            CostEntry.user_id == self.user_id
        ).group_by(
            CostEntry.cost_type
        ).all()
        
        # Convert enum members to their display values
        categories = [cost_type.value for cost_type, _ in results]
        amounts = [float(amount or 0) for _, amount in results]
        
        return {
            'categories': categories,
            'amounts': amounts
        }

    def get_lot_analytics(self, product_id: int) -> List[dict]:
        """
        Get analytics for inventory lots of a product.
        
        Args:
            product_id: ID of the product
            
        Returns:
            List[dict]: List of lot analytics with the following structure:
                {
                    'id': int,
                    'lot_number': str,
                    'received_date': str (ISO format) or None,
                    'expiration_date': str (ISO format) or None,
                    'expiration_status': str ('good'|'critical'|'expired'),
                    'quantity_received': int,
                    'quantity_remaining': int,
                    'total_units_sold': int,
                    'sell_through_rate': float,
                    'total_revenue': float,
                    'gross_margin': float,
                    'velocity': dict,
                    'unit_cost': float
                }
        """
        from app.models import InventoryLot, Product, OrderItem, Order
        from datetime import date
        from sqlalchemy import func
        
        try:
            # Get the product first to verify ownership and get pricing
            product = Product.query.options(
                db.joinedload(Product.lots),
                db.joinedload(Product.sales)
            ).get(product_id)
            
            if not product or product.user_id != self.user_id:
                return []
            
            # Pre-fetch all sales for this product to reduce queries
            sales_data = db.session.query(
                OrderItem.lot_id,
                func.sum(OrderItem.quantity).label('total_units_sold')
            ).filter(
                OrderItem.product_id == product_id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == self.user_id,
                Order.status == 'completed'
            ).group_by(OrderItem.lot_id).all()
            
            sales_by_lot = {lot_id: units for lot_id, units in sales_data}
            today = date.today()
            lot_analytics = []
            
            for lot in product.lots:
                units_sold = int(sales_by_lot.get(lot.id, 0))
                quantity_received = lot.quantity_received or 0
                unit_cost = float(lot.unit_cost or 0)
                
                # Calculate revenue and costs
                revenue = units_sold * product.selling_price_per_unit
                total_cost = units_sold * unit_cost
                
                # Calculate sell-through rate (percentage)
                sell_through_rate = 0.0
                if quantity_received > 0:
                    sell_through_rate = round((units_sold / quantity_received) * 100, 2)
                
                # Calculate gross margin (percentage)
                gross_margin = 0.0
                if revenue > 0 and total_cost > 0:
                    gross_margin = round(((revenue - total_cost) / revenue) * 100, 2)
                
                # Calculate velocity (units sold per day)
                velocity = 0.0
                if lot.received_date:
                    days_since_receipt = (today - lot.received_date).days
                    if days_since_receipt > 0:
                        velocity = round(units_sold / days_since_receipt, 2)
                
                # Determine expiration status
                expiration_status = 'good'
                if lot.expiration_date:
                    days_until_expiration = (lot.expiration_date - today).days
                    if days_until_expiration < 0:
                        expiration_status = 'expired'
                    elif days_until_expiration < 30:
                        expiration_status = 'critical'
                
                lot_analytics.append({
                    'id': lot.id,
                    'lot_number': lot.lot_number or f'Lot-{lot.id}',
                    'received_date': lot.received_date,
                    'expiration_date': lot.expiration_date,
                    'expiration_status': expiration_status,
                    'quantity_received': quantity_received,
                    'quantity_remaining': max(0, quantity_received - units_sold),
                    'total_units_sold': units_sold,
                    'sell_through_rate': sell_through_rate,
                    'total_revenue': float(revenue),
                    'gross_margin': gross_margin,
                    'velocity': {
                        'velocity': velocity,
                        'trend': 0  # Placeholder until historical lot-level trend is available
                    },
                    'unit_cost': unit_cost
                })
            
            return lot_analytics
            
        except Exception as e:
            # Log the error and return empty list to prevent frontend issues
            current_app.logger.error(f"Error in get_lot_analytics: {str(e)}", exc_info=True)
            return []

    def get_growth_metrics(self, product_id: int, periods: int = 6) -> List[dict]:
        """
        Get growth metrics for a product over time.
        
        Args:
            product_id: ID of the product
            periods: Number of periods to include
            
        Returns:
            List[dict]: Growth metrics by period with all values JSON-serializable
        """
        from datetime import datetime, timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=periods * 30)
        
        # SQLite compatible date grouping
        monthly_data = db.session.query(
            extract('year', Sales.created_at).label('year'),
            extract('month', Sales.created_at).label('month'),
            func.sum(Sales.units_sold * Product.selling_price_per_unit).label('revenue'),
            func.sum(Sales.units_sold).label('units')
        ).join(Product).filter(
            Sales.product_id == product_id,
            Product.user_id == self.user_id,
            Sales.created_at >= start_date
        ).group_by(
            extract('year', Sales.created_at),
            extract('month', Sales.created_at)
        ).order_by(
            extract('year', Sales.created_at),
            extract('month', Sales.created_at)
        ).all()
        
        growth_metrics = []
        previous_revenue = 0
        previous_units = 0
        
        for data in monthly_data:
            year = int(data.year)
            month = int(data.month)
            month_str = f"{year}-{month:02d}"
            
            revenue = float(data.revenue or 0)
            units = int(data.units or 0)
            
            # Calculate growth percentages
            revenue_growth = 0.0
            velocity_growth = 0.0
            
            if previous_revenue > 0:
                revenue_growth = ((revenue - previous_revenue) / previous_revenue) * 100
            
            if previous_units > 0:
                velocity_growth = ((units - previous_units) / previous_units) * 100
            
            growth_metrics.append({
                'period': month_str,  # Ensure this is a string
                'revenue': float(revenue),  # Convert to float for JSON serialization
                'units_sold': int(units),   # Convert to int for JSON serialization
                'revenue_growth': float(revenue_growth),  # Ensure float
                'velocity_growth': float(velocity_growth)  # Ensure float
            })
            
            previous_revenue = revenue
            previous_units = units
        
        return growth_metrics

    def get_monthly_metrics(self, months: int = 6) -> List[Dict[str, Any]]:
        """
        Get monthly metrics for the specified number of months.
        
        Args:
            months: Number of months of data to return
            
        Returns:
            List of dictionaries containing monthly metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30 * months)
            start_month = start_date.strftime('%Y-%m')
            end_month = end_date.strftime('%Y-%m')
            
            # Query sales data grouped by month
            monthly_sales = db.session.query(
                Sales.month,
                func.sum(Sales.units_sold * Product.selling_price_per_unit).label('total_sales'),
                func.count(Sales.id).label('order_count')
            ).join(
                Product, Sales.product_id == Product.id
            ).filter(
                Sales.user_id == self.user_id,
                Sales.month.between(start_month, end_month)
            ).group_by(
                Sales.month
            ).order_by(
                Sales.month
            ).all()
            
            # Format the results
            result = []
            for month_data in monthly_sales:
                result.append({
                    'month': month_data.month,
                    'total_sales': float(month_data.total_sales or 0),
                    'order_count': month_data.order_count,
                    'avg_order_value': float(month_data.total_sales / month_data.order_count) if month_data.order_count > 0 else 0
                })
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting monthly metrics: {e}", exc_info=True)
            return []

def get_dashboard_metrics(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get dashboard metrics for a user.
    
    This is a convenience function that creates a DashboardMetrics instance
    and returns the performance metrics.
    
    Args:
        user_id: Optional user ID. If not provided, uses current_user
        
    Returns:
        Dictionary containing dashboard metrics:
        - total_revenue: Formatted total revenue
        - total_orders: Total number of orders
        - avg_order_value: Formatted average order value
        - top_performers: List of top performing products
        - recent_sales: List of recent sales
        - inventory_status: Dictionary with inventory status counts
        
    Raises:
        AnalyticsError: If there's an error loading the metrics
    """
    try:
        metrics = DashboardMetrics(user_id=user_id)
        return metrics.get_performance_metrics()
    except Exception as e:
        logger.exception("Error in get_dashboard_metrics")
        if not isinstance(e, AnalyticsError):
            raise AnalyticsError(
                "Failed to load dashboard metrics",
                status_code=500
            ) from e
        raise

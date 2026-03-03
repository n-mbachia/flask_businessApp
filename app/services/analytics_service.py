"""
Analytics Service for generating sales reports and metrics from Orders and OrderItems.
This service uses materialized views for better performance with caching.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, extract, and_, or_, text, desc, case
from sqlalchemy.orm import aliased
from functools import wraps

import logging
from app import db, cache as app_cache
from app.models import Order, OrderItem, Product, Customer, User
from app.services.analytics_utils import AnalyticsError

# Import cache if available
cache = app_cache
HAS_CACHE = cache is not None
logger = logging.getLogger(__name__)


def cache_result(timeout=300, key_prefix="analytics", cache_empty=False):
    """
    Decorator to cache analytics results with improved error handling.
    
    Args:
        timeout: Cache timeout in seconds (default: 300)
        key_prefix: Prefix for cache keys
        cache_empty: Whether to cache empty results
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not HAS_CACHE:
                return f(*args, **kwargs)
            
            try:
                # Generate cache key
                cache_key = f"{key_prefix}:{f.__name__}:{str(args)}:{str(kwargs)}"
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = f(*args, **kwargs)
                
                # Cache result (optionally cache empty results)
                if result is not None or cache_empty:
                    cache.set(cache_key, result, timeout=timeout)
                
                return result
                
            except Exception as e:
                # Log cache error but don't fail the function
                logger.warning(f"Cache error in {f.__name__}: {str(e)}")
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator



class AnalyticsService:
    """Service for generating sales analytics and reports using optimized database views."""

    @staticmethod
    def get_product_revenue_trend(product_id: int, start_date, end_date, user_id: int):
        """Return revenue trend for a product over time."""
        sales = AnalyticsService.get_product_sales(user_id, product_id, start_date, end_date)
        # Example: return daily revenue trend
        return [{
            'date': str(start_date),
            'revenue': s['total_revenue']
        } for s in sales]

    @staticmethod
    def get_product_cost_breakdown(product_id: int, start_date, end_date, user_id: int):
        """Return cost breakdown for a product."""
        sales = AnalyticsService.get_product_sales(user_id, product_id, start_date, end_date)
        return [{
            'category': s['category'],
            'cogs': s['total_cogs'],
            'units_sold': s['units_sold']
        } for s in sales]

    @staticmethod
    def get_product_sales_performance(product_id: int, start_date, end_date, user_id: int):
        """Return sales performance for a product."""
        sales = AnalyticsService.get_product_sales(user_id, product_id, start_date, end_date)
        return [{
            'units_sold': s['units_sold'],
            'total_revenue': s['total_revenue'],
            'order_count': s['order_count']
        } for s in sales]

    @staticmethod
    def get_product_profit_margins(product_id: int, start_date, end_date, user_id: int):
        """Return profit margins for a product."""
        sales = AnalyticsService.get_product_sales(user_id, product_id, start_date, end_date)
        return [{
            'profit_margin': s['profit_margin'],
            'total_profit': s['total_profit']
        } for s in sales]

    @staticmethod
    def get_product_metrics(product_id: int, start_date, end_date, user_id: int):
        """Return general metrics for a product."""
        sales = AnalyticsService.get_product_sales(user_id, product_id, start_date, end_date)
        return [{
            'units_sold': s['units_sold'],
            'total_revenue': s['total_revenue'],
            'total_profit': s['total_profit'],
            'profit_margin': s['profit_margin'],
            'cogs': s['total_cogs'],
            'order_count': s['order_count']
        } for s in sales]

    @staticmethod
    @cache_result(timeout=300, key_prefix="monthly_sales")
    def get_sales_by_month(
        user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Get sales aggregated by month using monthly_sales_view.
        
        Args:
            user_id: The user ID to filter by
            year: Optional year to filter by
            month: Optional month to filter by  
            limit: Maximum number of months to return (1-100)
            
        Returns:
            List of monthly sales data dictionaries
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Invalid user ID")
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if year is not None and (not isinstance(year, int) or year < 2020 or year > datetime.now().year):
            raise ValueError("Invalid year range")
        if month is not None and (not isinstance(month, int) or month < 1 or month > 12):
            raise ValueError("Invalid month")
        
        # Optimized parameterized query with proper indexing hints
        query = text("""
            SELECT 
                year, month, 
                SUM(total_quantity) as units_sold,
                SUM(total_revenue) as total_revenue,
                COUNT(DISTINCT product_id) as product_count,
                SUM(customer_count) as customer_count,
                SUM(order_count) as order_count
            FROM monthly_sales_view
            WHERE user_id = :user_id
            AND (:year IS NULL OR year = :year)
            AND (:month IS NULL OR month = :month)
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT :limit
        """)
        
        params = {
            'user_id': user_id,
            'year': year,
            'month': month,
            'limit': limit
        }
        
        try:
            results = db.session.execute(query, params).fetchall()
        except Exception as e:
            logger.warning(f"Database error in get_sales_by_month (view fallback): {str(e)}")
            results = []

        if results:
            return [{
                'year': int(row[0]),
                'month': int(row[1]),
                'units_sold': int(row[2]) if row[2] else 0,
                'total_revenue': float(row[3]) if row[3] else 0.0,
                'product_count': int(row[4]) if row[4] else 0,
                'customer_count': int(row[5]) if row[5] else 0,
                'order_count': int(row[6]) if row[6] else 0
            } for row in results]

        # Fallback to direct orders aggregation (for tests or when view is unavailable)
        fallback_query = db.session.query(
            extract('year', Order.order_date).label('year'),
            extract('month', Order.order_date).label('month'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.count(Order.id).label('order_count')
        ).filter(
            Order.user_id == user_id
        )

        if year is not None:
            fallback_query = fallback_query.filter(extract('year', Order.order_date) == year)
        if month is not None:
            fallback_query = fallback_query.filter(extract('month', Order.order_date) == month)

        fallback_query = fallback_query.group_by('year', 'month').order_by(
            desc('year'), desc('month')
        ).limit(limit)

        try:
            fallback_results = fallback_query.all()
            return [{
                'year': int(row[0]),
                'month': int(row[1]),
                'units_sold': 0,
                'total_revenue': float(row[2]) if row[2] else 0.0,
                'product_count': 0,
                'customer_count': 0,
                'order_count': int(row[3]) if row[3] else 0
            } for row in fallback_results]
        except Exception as e:
            logger.warning(f"Database error in get_sales_by_month fallback: {str(e)}")
            return []

    @staticmethod
    def get_product_sales(
        user_id: int,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
        sort_by: str = 'revenue',
        sort_order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Get sales data for products using product_sales_view.
        
        Args:
            user_id: The user ID to filter by
            product_id: Optional product ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Optional maximum number of results (1-100)
            sort_by: Sort column ('revenue', 'units', 'profit', 'name')
            sort_order: Sort direction ('asc', 'desc')
            
        Returns:
            List of product sales data dictionaries
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Invalid user ID")
        if limit is not None and (not isinstance(limit, int) or limit < 1 or limit > 100):
            raise ValueError("Limit must be between 1 and 100")
        if sort_by not in ['revenue', 'units', 'profit', 'name']:
            raise ValueError("Invalid sort column")
        if sort_order not in ['asc', 'desc']:
            raise ValueError("Invalid sort order")
        
        sort_columns = {
            'revenue': 'total_revenue',
            'units': 'total_units_sold',
            'profit': 'total_profit',
            'name': 'product_name'
        }
        
        sort_column = sort_columns.get(sort_by, 'total_revenue')
        sort_dir = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        # Validate sort_column to prevent SQL injection
        allowed_sort_columns = {
            'revenue': 'total_revenue',
            'units': 'total_units_sold',
            'profit': 'total_profit',
            'name': 'product_name'
        }
        if sort_column not in allowed_sort_columns.values():
            raise ValueError(f"Invalid sort column: {sort_column}")
        
        # Validate sort_order
        if sort_dir not in ['ASC', 'DESC']:
            raise ValueError(f"Invalid sort order: {sort_dir}")
        
        # Secure parameterized query
        query = text(f"""
            SELECT 
                product_id,
                product_name,
                product_category,
                cogs_per_unit,
                selling_price_per_unit,
                total_units_sold,
                total_revenue,
                total_cogs,
                total_profit,
                customer_count,
                order_count
            FROM product_sales_view
            WHERE user_id = :user_id
            AND (:product_id IS NULL OR product_id = :product_id)
            AND (:start_date IS NULL OR order_date >= :start_date)
            AND (:end_date IS NULL OR order_date <= :end_date)
            ORDER BY {sort_column} {sort_dir}
            LIMIT :limit
        """)
        
        params = {
            'user_id': user_id,
            'product_id': product_id,
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit if limit else 1000  # High default for no limit
        }
        
        results = db.session.execute(query, params).fetchall()
        
        return [{
            'product_id': row[0],
            'product_name': row[1],
            'category': row[2],
            'cogs_per_unit': float(row[3]) if row[3] else 0.0,
            'selling_price_per_unit': float(row[4]) if row[4] else 0.0,
            'units_sold': int(row[5]) if row[5] else 0,
            'total_revenue': float(row[6]) if row[6] else 0.0,
            'total_cogs': float(row[7]) if row[7] else 0.0,
            'total_profit': float(row[8]) if row[8] else 0.0,
            'customer_count': int(row[9]) if row[9] else 0,
            'order_count': int(row[10]) if row[10] else 0,
            'profit_margin': (float(row[8]) / float(row[6])) * 100 if row[6] and float(row[6]) > 0 else 0.0
        } for row in results]

    @staticmethod
    def get_customer_sales(
        user_id: int,
        customer_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
        sort_by: str = 'total_spent',
        sort_order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Get sales data by customer using the customer_sales_view.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Invalid user ID")
        if limit is not None and (not isinstance(limit, int) or limit < 1 or limit > 100):
            raise ValueError("Limit must be between 1 and 100")

        sort_columns = {
            'spent': 'total_spent',
            'orders': 'order_count',
            'products': 'unique_products_purchased',
            'name': 'customer_name',
            'recent': 'last_purchase_date'
        }
        
        sort_column = sort_columns.get(sort_by, 'total_spent')
        sort_dir = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        params = {'user_id': user_id}
        customer_filter = ""
        date_filter = ""
        
        if customer_id:
            customer_filter = "AND customer_id = :customer_id"
            params['customer_id'] = customer_id
            
        if start_date or end_date:
            date_conditions = []
            if start_date:
                date_conditions.append("last_purchase_date >= :start_date")
                params['start_date'] = start_date
            if end_date:
                date_conditions.append("last_purchase_date <= :end_date")
                params['end_date'] = end_date
                
            if date_conditions:
                date_filter = f"AND ({' AND '.join(date_conditions)})"
                
        limit_clause = ""
        if limit:
            limit_clause = "LIMIT :limit"
            params['limit'] = limit
        else:
            limit_clause = ""
        
        # Validate sort_column to prevent SQL injection
        allowed_sort_columns = {
            'spent': 'total_spent',
            'orders': 'order_count', 
            'products': 'unique_products_purchased',
            'name': 'customer_name',
            'recent': 'last_purchase_date',
            'total_spent': 'total_spent'
        }
        if sort_column not in allowed_sort_columns.values():
            raise ValueError(f"Invalid sort column: {sort_column}")
        
        # Validate sort_order
        if sort_dir not in ['ASC', 'DESC']:
            raise ValueError(f"Invalid sort order: {sort_dir}")
        
        # Secure parameterized query
        query = text(f"""
            SELECT 
                customer_id,
                customer_name,
                customer_email,
                order_count,
                unique_products_purchased,
                total_units_purchased,
                total_spent,
                first_purchase_date,
                last_purchase_date
            FROM customer_sales_view
            WHERE user_id = :user_id
            {customer_filter}
            {date_filter}
            ORDER BY {sort_column} {sort_dir}
            {limit_clause}
        """)
        
        results = db.session.execute(query, params).fetchall()
        
        return [{
            'customer_id': row[0],
            'customer_name': row[1],
            'customer_email': row[2],
            'order_count': int(row[3]) if row[3] else 0,
            'unique_products_purchased': int(row[4]) if row[4] else 0,
            'total_units_purchased': int(row[5]) if row[5] else 0,
            'total_spent': float(row[6]) if row[6] else 0.0,
            'first_purchase_date': row[7].isoformat() if row[7] else None,
            'last_purchase_date': row[8].isoformat() if row[8] else None,
            'avg_order_value': float(row[6]) / int(row[3]) if row[3] and int(row[3]) > 0 else 0.0
        } for row in results]

    @staticmethod
    def get_sales_summary(
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of sales metrics using the daily_sales_view.
        """
        # Get summary from daily_sales_view
        query = text("""
            SELECT 
                COALESCE(SUM(total_revenue), 0) as total_revenue,
                COALESCE(SUM(order_count), 0) as order_count,
                COALESCE(SUM(customer_count), 0) as customer_count,
                COALESCE(SUM(unique_products_sold), 0) as unique_products_sold,
                COALESCE(SUM(total_units_sold), 0) as total_units_sold,
                COALESCE(AVG(avg_order_value), 0) as avg_order_value
            FROM daily_sales_view
            WHERE user_id = :user_id
            {date_filter}
        """)
        
        params = {'user_id': user_id}
        date_filter = ""
        
        if start_date or end_date:
            date_conditions = []
            if start_date:
                date_conditions.append("sale_date >= :start_date")
                params['start_date'] = start_date
            if end_date:
                date_conditions.append("sale_date <= :end_date")
                params['end_date'] = end_date
                
            if date_conditions:
                date_filter = f"AND ({' AND '.join(date_conditions)})"
        
        query = query.format(date_filter=date_filter)
        result = db.session.execute(query, params).fetchone()
        
        # Get top products
        top_products = AnalyticsService.get_product_sales(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=5,
            sort_by='revenue'
        )
        
        # Get top customers
        top_customers = AnalyticsService.get_customer_sales(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=5,
            sort_by='spent'
        )
        
        # Get sales by category
        category_query = text("""
            SELECT 
                category,
                SUM(total_units_sold) as units_sold,
                SUM(total_revenue) as revenue,
                SUM(total_profit) as profit
            FROM category_sales_view
            WHERE user_id = :user_id
            {date_filter}
            GROUP BY category
            ORDER BY revenue DESC
        """)
        
        date_filter = ""
        if start_date or end_date:
            date_conditions = []
            if start_date:
                date_conditions.append("product_id IN ("
                                    "SELECT DISTINCT oi.product_id FROM orders o "
                                    "JOIN order_items oi ON o.id = oi.order_id "
                                    "WHERE o.user_id = :user_id AND DATE(o.order_date) >= :start_date")
                if end_date:
                    date_conditions.append("DATE(o.order_date) <= :end_date")
                date_conditions.append(")")
                date_filter = f"AND ({' AND '.join(date_conditions)})"
        
        category_query = category_query.format(date_filter=date_filter)
        category_results = db.session.execute(category_query, params).fetchall()
        
        sales_by_category = [{
            'category': row[0],
            'units_sold': int(row[1]) if row[1] else 0,
            'revenue': float(row[2]) if row[2] else 0.0,
            'profit': float(row[3]) if row[3] else 0.0,
            'profit_margin': (float(row[3]) / float(row[2])) * 100 if row[2] and float(row[2]) > 0 else 0.0
        } for row in category_results]
        
        return {
            'total_revenue': float(result[0]) if result[0] else 0.0,
            'order_count': int(result[1]) if result[1] else 0,
            'customer_count': int(result[2]) if result[2] else 0,
            'unique_products_sold': int(result[3]) if result[3] else 0,
            'total_units_sold': int(result[4]) if result[4] else 0,
            'avg_order_value': float(result[5]) if result[5] else 0.0,
            'top_products': top_products,
            'top_customers': top_customers,
            'sales_by_category': sales_by_category
        }

    @staticmethod
    def get_inventory_summary(user_id: int) -> Dict[str, Any]:
        """
        Get inventory analytics summary for a user.
        
        Args:
            user_id: The user ID to filter by
            
        Returns:
            Dictionary with inventory summary data
            
        Raises:
            ValueError: If user_id is invalid
        """
        if user_id <= 0:
            raise ValueError("Invalid user ID")
        
        # Get inventory data using secure query
        query = text("""
            SELECT 
                COUNT(*) as total_items,
                SUM(CASE WHEN ii.quantity <= ii.reorder_level THEN 1 ELSE 0 END) as low_stock_count,
                SUM(ii.quantity * p.price) as inventory_value,
                p.category
            FROM inventory_items ii
            JOIN products p ON ii.product_id = p.id
            WHERE p.user_id = :user_id
            GROUP BY p.category
        """)
        
        results = db.session.execute(query, {'user_id': user_id}).fetchall()
        
        # Calculate totals and categories
        total_items = sum(row[0] for row in results)
        low_stock_count = sum(row[1] for row in results)
        inventory_value = sum(row[2] for row in results if row[2] is not None)
        
        # Group by category
        categories = {}
        for row in results:
            category = row[3] or 'Uncategorized'
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'value': 0.0,
                    'low_stock': 0
                }
            categories[category]['count'] += row[0]
            categories[category]['value'] += float(row[2]) if row[2] else 0.0
            categories[category]['low_stock'] += row[1]
        
        return {
            'total_items': total_items,
            'low_stock_items': low_stock_count,
            'inventory_value': float(inventory_value) if inventory_value else 0.0,
            'categories': [{
                'name': name,
                'count': data['count'],
                'value': float(data['value']),
                'low_stock': data['low_stock']
            } for name, data in categories.items()]
        }

    @classmethod
    def refresh_analytics_views(cls):
        """Refresh all materialized views to ensure data is up to date."""
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_sales_view"))
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY product_sales_view"))
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY customer_sales_view"))
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_view"))
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY category_sales_view"))
        db.session.commit()

"""
Trend Analysis Services

This module provides functionality for analyzing sales and product trends over time.
It includes functions for calculating monthly sales, product performance metrics,
and generating trend analysis reports.
"""

from typing import Dict, List, Tuple, Optional, Any, Literal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from sqlalchemy import func, desc, and_
from flask_login import current_user
import logging

# For Python < 3.8 compatibility
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from app import db
from app.models.sales import Sales
from app.models.products import Product
from app.utils.decorators import handle_exceptions, performance_log, track_performance
from app.utils.cache import cached

# Set up logging
logger = logging.getLogger(__name__)

# Type aliases
Period = Literal['1m', '3m', '6m', '1y', '2y', 'all']
TrendData = Dict[date, float]  # Maps dates to sales amounts
ProductPerformance = Dict[str, Dict[str, Any]]  # Product ID -> Product metrics

class TrendAnalysisResult(TypedDict):
    """Type definition for trend analysis results."""
    current_year: TrendData
    previous_year: Optional[TrendData]
    product_performance: ProductPerformance
    summary: Dict[str, float]


@handle_exceptions
@performance_log
@track_performance('trends_analysis')
@cached(timeout=300, key_prefix=lambda: f'product_analytics_{current_user.id if current_user.is_authenticated else "anonymous"}')
def get_trends_analysis(
    user_id: int,
    period: Period = '5m',
    product_id: Optional[int] = None
) -> TrendAnalysisResult:
    """
    Generate trend analysis for the specified period.
    
    Args:
        user_id: ID of the user to analyze
        period: Time period for analysis ('1m', '3m', '6m', '1y', '2y', 'all')
        product_id: Optional product ID to filter by
        
    Returns:
        TrendAnalysisResult: Dictionary containing trend analysis data with the following structure:
        {
            'current_year': Dict[date, float],  # Sales data for current year
            'previous_year': Optional[Dict[date, float]],  # Sales data for previous year
            'product_performance': Dict[str, Dict[str, Any]],  # Product metrics
            'summary': Dict[str, float]  # Summary metrics
        }
    """
    # Default response with empty data
    default_response: TrendAnalysisResult = {
        'current_year': {},
        'previous_year': None,
        'product_performance': {},
        'summary': {
            'total_sales': 0.0,
            'yoy_growth': 0.0,
            'total_products': 0,
            'total_revenue': 0.0,
            'avg_revenue_per_product': 0.0
        }
    }

    try:
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            return default_response
            
        # Validate period
        period_map = {'1m': 1, '3m': 3, '6m': 6, '1y': 12, '2y': 24, 'all': None}
        if period not in period_map:
            logger.warning(f"Invalid period '{period}'. Defaulting to '5m'")
            period = '5m'
        month_count = period_map.get(period, 5)
        
        # Get current and previous year data
        end_date = datetime.utcnow()
        current_year = end_date.year
        previous_year = current_year - 1
        
        try:
            # Fetch sales data with error handling
            monthly_sales = _get_monthly_sales(user_id, current_year, product_id)
            previous_year_sales = _get_monthly_sales(user_id, previous_year, product_id)
            
            # Get product performance with error handling
            product_performance = _get_product_performance(user_id, current_year, product_id)
            
            # Initialize trend data structure
            trends = _initialize_trends(month_count or 12)  # Default to 12 months if period is 'all'
            
            # Fill in the trends with actual data
            if monthly_sales:
                _fill_trends_with_sales_data(trends, monthly_sales, is_current_year=True)
            
            if previous_year_sales:
                _fill_trends_with_sales_data(trends, previous_year_sales, is_current_year=False)
            
            # Process product performance data if available
            if product_performance:
                _process_product_performance(trends, product_performance)
            
            # Calculate summary metrics
            summary = _calculate_summary_metrics(trends)
            
            # Prepare final response
            result: TrendAnalysisResult = {
                'current_year': trends.get('current_year', {}),
                'previous_year': trends.get('previous_year'),
                'product_performance': trends.get('products', {}),
                'summary': summary
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating trend analysis: {str(e)}", exc_info=True)
            return default_response
            
    except Exception as e:
        logger.critical(f"Critical error in get_trends_analysis: {str(e)}", exc_info=True)
        return default_response


def _get_monthly_sales(
    user_id: int,
    year: int,
    product_id: Optional[int] = None
) -> List[Tuple[date, float]]:
    """
    Get monthly sales data for a specific year.
    
    Args:
        user_id: ID of the user
        year: Year to get sales for
        product_id: Optional product ID to filter by
        
    Returns:
        List of tuples containing (date, total_sales)
    """
    try:
        # Convert year to string for comparison with Sales.month (format: 'YYYY-MM')
        year_str = str(year)
        
        # Use SQLite-compatible string concatenation
        query = db.session.query(
            (Sales.month + '-01').label('month'),  # SQLite compatible concatenation
            func.sum(Sales.units_sold * Product.selling_price_per_unit).label('total_sales')
        ).join(
            Product, Sales.product_id == Product.id
        ).filter(
            Sales.user_id == user_id,
            Sales.month.startswith(year_str)  # Filter by year prefix
        )
        
        if product_id is not None:
            query = query.filter(Sales.product_id == product_id)
            
        results = query.group_by(Sales.month)
        
        # Convert month strings to date objects (first day of each month)
        return [
            (datetime.strptime(r.month, '%Y-%m-%d').date(), float(r.total_sales or 0))
            for r in results
        ]
        
    except Exception as e:
        logger.error(f"Error fetching monthly sales for user {user_id}, year {year}: {str(e)}", exc_info=True)
        return []


def _get_product_performance(
    user_id: int,
    year: int,
    product_id: Optional[int] = None
) -> List[Tuple[int, str, int, float]]:
    """
    Get product performance metrics for a specific year.
    
    Args:
        user_id: ID of the user
        year: Year to get performance for
        product_id: Optional product ID to filter by
        
    Returns:
        List of tuples containing (product_id, product_name, units_sold, total_revenue)
    """
    try:
        # Convert year to string for comparison with Sales.month (format: 'YYYY-MM')
        year_str = str(year)
        
        # Build the base query
        query = db.session.query(
            Product.id,
            Product.name,
            func.sum(Sales.units_sold).label('units_sold'),
            func.sum(Sales.units_sold * Product.selling_price_per_unit).label('total_revenue')
        ).join(
            Sales, Product.id == Sales.product_id
        ).filter(
            Sales.user_id == user_id,
            Sales.month.startswith(year_str)  # Filter by year prefix
        )
        
        if product_id is not None:
            query = query.filter(Product.id == product_id)
            
        # Group by product and order by total revenue (descending)
        results = query.group_by(
            Product.id,
            Product.name
        ).order_by(
            func.sum(Sales.units_sold * Product.selling_price_per_unit).desc()
        ).all()
        
        # Convert results to the expected format
        product_performance = []
        for product_id, product_name, units_sold, total_revenue in results:
            try:
                # Ensure we have valid numeric values
                units = int(units_sold or 0)
                revenue = float(total_revenue or 0)
                product_performance.append((product_id, product_name, units, revenue))
            except (TypeError, ValueError) as e:
                logger.error(f"Error processing product performance for product {product_id}: {str(e)}")
                continue
                
        return product_performance
        
    except Exception as e:
        logger.error(f"Error fetching product performance for user {user_id}, year {year}: {str(e)}", exc_info=True)
        return []


def _initialize_trends(month_count: int) -> Dict[str, Any]:
    """
    Initialize the trends data structure with empty values.
    
    Args:
        month_count: Number of months to include in the trend analysis
        
    Returns:
        Dictionary with the following structure:
        {
            'current_year': Dict[date, float],  # Will store sales data for current year
            'previous_year': Dict[date, float],  # Will store sales data for previous year
            'products': Dict[str, Dict[str, Any]],  # Will store product performance data
            'months': List[date]  # List of month start dates in the analysis period
        }
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - relativedelta(months=month_count-1)
        
        # Generate list of month start dates in the range
        months: List[date] = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months.append(current.date())
            # Move to the first day of the next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)
        
        return {
            'current_year': {},
            'previous_year': {},
            'products': {},
            'months': months
        }
        
    except Exception as e:
        logger.error(f"Error initializing trends data structure: {str(e)}", exc_info=True)
        # Return empty structure on error
        return {
            'current_year': {},
            'previous_year': {},
            'products': {},
            'months': []
        }


def _fill_trends_with_sales_data(
    trends: Dict[str, Any],
    sales_data: List[Tuple[date, float]],
    is_current_year: bool
) -> None:
    """
    Fill trends data structure with sales data.
    
    Args:
        trends: The trends dictionary to fill
        sales_data: List of (sale_date, amount) tuples
        is_current_year: Whether this is for the current year
    """
    year_key = 'current_year' if is_current_year else 'previous_year'
    
    # Initialize monthly data with zeros
    for month in trends['months']:
        trends[year_key][month] = 0.0
    
    # Fill in actual sales data
    for sale_date, amount in sales_data:
        try:
            # Ensure we have a date object
            if not isinstance(sale_date, date):
                if isinstance(sale_date, str):
                    # Handle different date string formats
                    if len(sale_date) == 7:  # YYYY-MM
                        sale_date = datetime.strptime(sale_date + '-01', '%Y-%m-%d').date()
                    else:
                        sale_date = datetime.strptime(sale_date.split('T')[0], '%Y-%m-%d').date()
                else:
                    logger.warning(f"Unexpected sale date format: {sale_date}")
                    continue
            
            # Find the first day of the month for the sale date
            month_start = sale_date.replace(day=1)
            if month_start in trends[year_key]:
                trends[year_key][month_start] += float(amount or 0)
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing sale date {sale_date}: {str(e)}")
            continue


def _process_product_performance(
    trends: Dict[str, Any],
    product_data: List[Tuple[int, str, int, float]]
) -> None:
    """
    Process product performance data into the trends structure.
    
    Args:
        trends: The trends dictionary to update
        product_data: List of (product_id, product_name, units_sold, revenue) tuples
    """
    for product_id, product_name, units_sold, revenue in product_data:
        try:
            # Ensure we have valid numeric values
            product_id_str = str(int(product_id))
            units = int(units_sold or 0)
            revenue_float = float(revenue or 0)
            
            trends['products'][product_id_str] = {
                'name': str(product_name),
                'units_sold': units,
                'revenue': revenue_float
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing product {product_id} data: {str(e)}")
            continue


def _calculate_summary_metrics(trends: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate summary metrics from trends data.
    
    Args:
        trends: Dictionary containing trend data
        
    Returns:
        Dictionary with calculated metrics
    """
    try:
        # Safely calculate current year sales
        current_year_sales = sum(
            float(amount) 
            for amount in trends.get('current_year', {}).values() 
            if amount is not None
        )
        
        # Safely calculate previous year sales
        previous_year_sales = sum(
            float(amount) 
            for amount in trends.get('previous_year', {}).values() 
            if amount is not None
        )
        
        # Calculate year-over-year growth with safe division
        yoy_growth = 0.0
        if previous_year_sales > 0:
            yoy_growth = ((current_year_sales - previous_year_sales) / previous_year_sales) * 100
        
        # Process product metrics
        products = trends.get('products', {})
        total_products = len(products)
        
        # Safely calculate total revenue
        total_revenue = 0.0
        for product in products.values():
            try:
                total_revenue += float(product.get('revenue', 0))
            except (TypeError, ValueError):
                continue
        
        # Calculate average revenue per product with safe division
        avg_revenue_per_product = 0.0
        if total_products > 0:
            avg_revenue_per_product = total_revenue / total_products
        
        return {
            'total_sales': round(current_year_sales, 2),
            'yoy_growth': round(yoy_growth, 2),
            'total_products': total_products,
            'total_revenue': round(total_revenue, 2),
            'avg_revenue_per_product': round(avg_revenue_per_product, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating summary metrics: {str(e)}", exc_info=True)
        # Return safe defaults in case of error
        return {
            'total_sales': 0.0,
            'yoy_growth': 0.0,
            'total_products': 0,
            'total_revenue': 0.0,
            'avg_revenue_per_product': 0.0
        }

"""
Profit calculation service for the business application.

This module provides the ProfitCalculator class which handles all profit-related
calculations including gross profit, operating profit, and net profit.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple, Union
import logging

from sqlalchemy import text, func

from app import db
from app.models import (
    Product, 
    CostEntry,
    CostTypeEnum,
    Sales,
)

try:
    from app.utils import format_currency
    _HAS_FORMAT_CURRENCY = True
except ImportError:
    format_currency = lambda value, currency='KES', grouping=True: str(value) if value else ""
    _HAS_FORMAT_CURRENCY = False

# Initialize logger
logger = logging.getLogger(__name__)

class ProfitCalculator:
    """
    A service class for calculating various profit metrics.
    
    This class provides methods to calculate different types of profit metrics
    including gross profit, operating profit, and net profit for different
    time periods and products.
    """
    
    def __init__(self, user_id: int):
        """
        Initialize the ProfitCalculator with a user ID.
        
        Args:
            user_id: The ID of the user to calculate profits for
        """
        self.user_id = user_id
    
    def calculate_gross_profit(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        Calculate gross profit (Revenue - COGS) for a given date range.
        
        Args:
            start_date: Start date for the calculation
            end_date: End date for the calculation
            
        Returns:
            Dictionary containing gross profit and related metrics
        """
        # Get revenue and COGS from the product_sales_view
        query = text("""
            SELECT 
                COALESCE(SUM(total_revenue), 0) as revenue,
                COALESCE(SUM(total_cogs), 0) as cogs
            FROM product_sales_view
            WHERE user_id = :user_id
            AND product_id IN (
                SELECT DISTINCT oi.product_id 
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = :user_id
                AND o.order_date BETWEEN :start_date AND :end_date
                AND o.status = 'completed'
            )
        """)
        
        result = db.session.execute(query, {
            'user_id': self.user_id,
            'start_date': start_date,
            'end_date': end_date
        }).fetchone()
        
        revenue = float(result[0]) if result[0] else 0.0
        cogs = float(result[1]) if result[1] else 0.0
        gross_profit = revenue - cogs
        
        return {
            'gross_profit': gross_profit,
            'revenue': revenue,
            'cogs': cogs,
            'gross_margin': (gross_profit / revenue * 100) if revenue > 0 else 0.0
        }
    
    def calculate_operating_profit(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        Calculate operating profit (Gross Profit - Operating Expenses) for a date range.
        
        Args:
            start_date: Start date for the calculation
            end_date: End date for the calculation
            
        Returns:
            Dictionary containing operating metrics including expenses by category
        """
        # Get gross profit first
        gross = self.calculate_gross_profit(start_date, end_date)
        
        # Get all operating expenses (non-COGS)
        expenses = db.session.query(CostEntry).filter(
            CostEntry.user_id == self.user_id,
            CostEntry.date.between(start_date, end_date),
            ~CostEntry.cost_type.in_([
                CostTypeEnum.RAW_MATERIALS.value,
                CostTypeEnum.DIRECT_LABOR.value,
                CostTypeEnum.PACKAGING.value
            ]),
            CostEntry.is_direct == False
        ).all()
        
        # Calculate total operating expenses
        total_operating_expenses = float(sum(exp.amount for exp in expenses))
        
        # Calculate operating profit and margin
        operating_profit = gross['gross_profit'] - total_operating_expenses
        operating_margin = (operating_profit / gross['revenue'] * 100) if gross['revenue'] > 0 else 0.0
        
        # Categorize expenses
        expense_categories = {
            'fixed': 0.0,
            'variable': 0.0,
            'semi_variable': 0.0
        }
        
        for exp in expenses:
            amount = float(exp.amount)
            if exp.is_fixed_cost:
                expense_categories['fixed'] += amount
            elif exp.is_variable_cost:
                expense_categories['variable'] += amount
            else:
                expense_categories['semi_variable'] += amount
        
        return {
            'gross_profit': gross['gross_profit'],
            'operating_expenses': total_operating_expenses,
            'operating_profit': operating_profit,
            'operating_margin': operating_margin,
            'expense_categories': expense_categories
        }
    
    def calculate_net_profit(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        Calculate net profit (Operating Profit - Other Expenses) for a date range.
        
        In this implementation, we're considering operating profit as net profit
        since we're not accounting for taxes or interest. This can be extended
        to include those factors if needed.
        
        Args:
            start_date: Start date for the calculation
            end_date: End date for the calculation
            
        Returns:
            Dictionary containing all profit metrics
        """
        operating = self.calculate_operating_profit(start_date, end_date)
        
        # For now, operating profit is the same as net profit
        # We can add tax and interest calculations here if needed
        net_profit = operating['operating_profit']
        net_margin = operating['operating_margin']
        
        return {
            **operating,
            'net_profit': net_profit,
            'net_margin': net_margin
        }
    
    def get_profit_summary(
        self, 
        year_month: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Get profit summary for a specific month or custom date range.
        
        Args:
            year_month: Month in 'YYYY-MM' format (mutually exclusive with start_date/end_date)
            start_date: Start date for custom date range
            end_date: End date for custom date range
            
        Returns:
            Dictionary containing all profit metrics for the specified period
            
        Raises:
            ValueError: If date parameters are invalid
        """
        if year_month and (start_date or end_date):
            raise ValueError("Cannot specify both year_month and start_date/end_date")
            
        if year_month:
            # Parse year and month
            try:
                year, month = map(int, year_month.split('-'))
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            except (ValueError, IndexError):
                raise ValueError("Invalid year_month format. Use 'YYYY-MM'")
        elif not (start_date and end_date):
            # Default to current month if no dates provided
            today = datetime.utcnow()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        return self.calculate_net_profit(start_date, end_date)
    
    def get_profit_trends(
        self, 
        months: int = 12, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, list]:
        """
        Get profit trends over the specified number of months.
        
        Args:
            months: Number of months to include in the trend
            end_date: End date for the trend (defaults to current date)
            
        Returns:
            Dictionary containing monthly profit data with default values if no data exists
        """
        if end_date is None:
            end_date = datetime.utcnow()
            
        # Calculate start date
        start_date = end_date - timedelta(days=30 * months)
        
        # Generate month labels
        months_data = []
        current = start_date.replace(day=1)
        
        while current <= end_date:
            months_data.append({
                'month': current.strftime('%Y-%m'),
                'label': current.strftime('%b %Y'),
                'start_date': current.replace(day=1),
                'end_date': (
                    current.replace(month=current.month % 12 + 1, day=1) - timedelta(days=1)
                    if current.month < 12
                    else current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
                )
            })
            
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Initialize trends with default values
        trends = {
            'months': [],
            'revenue': [],
            'gross_profit': [],
            'operating_profit': [],
            'net_profit': [],
            'gross_margin': [],
            'operating_margin': [],
            'net_margin': [],
            'monthly': []  
        }
        
        has_data = False
        
        for month_data in months_data:
            try:
                # Get metrics for the month
                metrics = self.get_profit_summary(
                    year_month=month_data['month']
                )
                
                # If we have any non-zero metric, consider it valid data
                if any(float(metrics.get(key, 0)) > 0 for key in ['revenue', 'gross_profit', 'operating_profit', 'net_profit']):
                    has_data = True
                
                # Append data to trends with proper defaults
                month_metrics = {
                    'revenue': float(metrics.get('revenue', 0)),
                    'gross_profit': float(metrics.get('gross_profit', 0)),
                    'operating_profit': float(metrics.get('operating_profit', 0)),
                    'net_profit': float(metrics.get('net_profit', 0)),
                    'gross_margin': float(metrics.get('gross_margin', 0)),
                    'operating_margin': float(metrics.get('operating_margin', 0)),
                    'net_margin': float(metrics.get('net_margin', 0))
                }
                
                trends['months'].append(month_data['label'])
                trends['revenue'].append(month_metrics['revenue'])
                trends['gross_profit'].append(month_metrics['gross_profit'])
                trends['operating_profit'].append(month_metrics['operating_profit'])
                trends['net_profit'].append(month_metrics['net_profit'])
                trends['gross_margin'].append(month_metrics['gross_margin'])
                trends['operating_margin'].append(month_metrics['operating_margin'])
                trends['net_margin'].append(month_metrics['net_margin'])
                
                # Add to monthly data in the format expected by the frontend
                trends['monthly'].append({
                    'month': month_data['month'],
                    'revenue': month_metrics['revenue'],
                    'profit': month_metrics['net_profit'],
                    'gross_profit': month_metrics['gross_profit'],
                    'operating_profit': month_metrics['operating_profit'],
                    'gross_margin': month_metrics['gross_margin'],
                    'net_margin': month_metrics['net_margin'],
                    'label': month_data['label']
                })
                
            except Exception as e:
                logger.error(f"Error calculating trends for {month_data['month']}: {e}")
                # Add zeros for this month if there's an error
                trends['months'].append(month_data['label'])
                trends['revenue'].append(0.0)
                trends['gross_profit'].append(0.0)
                trends['operating_profit'].append(0.0)
                trends['net_profit'].append(0.0)
                trends['gross_margin'].append(0.0)
                trends['operating_margin'].append(0.0)
                trends['net_margin'].append(0.0)
                trends['monthly'].append({
                    'month': month_data['month'],
                    'revenue': 0.0,
                    'profit': 0.0,
                    'gross_profit': 0.0,
                    'operating_profit': 0.0,
                    'gross_margin': 0.0,
                    'net_margin': 0.0,
                    'label': month_data['label']
                })
        
        # If no data was found, log a warning but still return the trends with zeros
        if not has_data:
            logger.warning(f"No profit data found for user {self.user_id} in the last {months} months")
        
        return trends
    
    def get_product_profitability(
        self, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 10
    ) -> list:
        """
        Get profitability metrics by product.
        
        Args:
            start_date: Start date for the calculation
            end_date: End date for the calculation
            limit: Maximum number of products to return
            
        Returns:
            List of dictionaries with product profitability data
        """
        try:
            # Format dates as YYYY-MM strings for comparison with Sales.month
            start_month = start_date.strftime('%Y-%m')
            end_month = end_date.strftime('%Y-%m')
            
            # Get sales data by product with category
            sales_by_product = db.session.query(
                Product.id,
                Product.name,
                Product.category,
                func.coalesce(func.sum(Sales.units_sold * Product.selling_price_per_unit), 0).label('revenue'),
                func.coalesce(func.sum(Sales.units_sold * Product.cogs_per_unit), 0).label('cogs'),
                func.count(Sales.id).label('sales_count')
            ).outerjoin(
                Sales, 
                (Product.id == Sales.product_id) & 
                (Sales.month.between(start_month, end_month))
            ).filter(
                Product.user_id == self.user_id
            ).group_by(
                Product.id,
                Product.name,
                Product.category
            ).order_by(
                func.coalesce(func.sum(Sales.units_sold * Product.selling_price_per_unit), 0).desc()
            ).limit(limit).all()
            
            # Get total revenue for shared cost allocation
            total_revenue_result = db.session.query(
                func.coalesce(func.sum(Sales.units_sold * Product.selling_price_per_unit), 0)
            ).join(Product).filter(
                Sales.month.between(start_month, end_month),
                Product.user_id == self.user_id
            ).scalar()
            
            total_revenue = float(total_revenue_result) if total_revenue_result else 0.0
            
            # Get total shared costs (non-direct costs)
            shared_costs_result = db.session.query(
                func.coalesce(func.sum(CostEntry.amount), 0)
            ).filter(
                CostEntry.user_id == self.user_id,
                CostEntry.date.between(start_date, end_date),
                CostEntry.is_direct == False
            ).scalar()
            
            total_shared_costs = float(shared_costs_result) if shared_costs_result else 0.0
            
            # Calculate profitability for each product
            products = []
            for sale in sales_by_product:
                revenue = float(sale.revenue) if sale.revenue else 0.0
                cogs = float(sale.cogs) if sale.cogs else 0.0
                gross_profit = revenue - cogs
                
                # Allocate shared costs based on revenue proportion
                revenue_share = (revenue / total_revenue) if total_revenue > 0 else 0
                allocated_shared_cost = total_shared_costs * revenue_share
                
                # Calculate direct costs for this product
                direct_cost_result = db.session.query(
                    func.coalesce(func.sum(CostEntry.amount), 0)
                ).filter(
                    CostEntry.user_id == self.user_id,
                    CostEntry.date.between(start_date, end_date),
                    CostEntry.is_direct == True,
                    CostEntry.product_id == sale.id
                ).scalar()
                
                direct_cost = float(direct_cost_result) if direct_cost_result else 0.0
                
                # Calculate total cost and net profit
                total_cost = direct_cost + allocated_shared_cost
                net_profit = gross_profit - total_cost
                
                # Calculate margins
                gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0
                net_margin = (net_profit / revenue * 100) if revenue > 0 else 0.0
                
                products.append({
                    'id': sale.id,
                    'name': sale.name,
                    'category': sale.category or 'Uncategorized',
                    'revenue': revenue,
                    'cogs': cogs,
                    'gross_profit': gross_profit,
                    'profit': net_profit,  
                    'margin': net_margin,  
                    'gross_margin': gross_margin,
                    'direct_costs': direct_cost,
                    'allocated_shared_costs': allocated_shared_cost,
                    'total_costs': total_cost,
                    'net_profit': net_profit,
                    'net_margin': net_margin,
                    'sales_count': sale.sales_count
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Error in get_product_profitability: {str(e)}", exc_info=True)
            return []

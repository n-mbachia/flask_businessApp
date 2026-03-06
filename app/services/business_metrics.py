# app/services/business_metrics.py

"""
Business Metrics Service

This module provides comprehensive business performance metrics and analytics.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import func, and_, or_
from decimal import Decimal, InvalidOperation
from app import db
from app.models import Order, OrderItem, Product
from app.models.costs import CostEntry, CostTypeEnum
import logging

logger = logging.getLogger(__name__)


class BusinessMetricsError(Exception):
    """Base exception for business metrics errors."""
    pass


class BusinessMetrics:
    """Service class for calculating and providing business metrics."""
    
    def __init__(self, user_id: int):
        """Initialize with the current user's ID."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Invalid user ID provided")
        self.user_id = user_id

    def get_financial_health(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive financial health metrics.
        
        Returns:
            dict: Dictionary containing financial metrics including revenue, expenses,
                  profitability, cash flow, and working capital metrics.
                  
        Raises:
            BusinessMetricsError: If calculation fails
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                start_date = end_date.replace(day=1)
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            metrics_period = end_date.strftime('%Y-%m')
            
            # Get all metrics
            revenue_metrics = self._get_revenue_metrics(start_date, end_date)
            expense_metrics = self._get_expense_metrics(start_date, end_date)
            
            return {
                'revenue': revenue_metrics,
                'expenses': expense_metrics,
                'profitability': self._get_profitability_metrics(
                    revenue_metrics,
                    expense_metrics,
                    start_date,
                    end_date
                ),
                'cash_flow': self._get_cash_flow_metrics(start_date, end_date),
                'working_capital': self._get_working_capital_metrics(),
                'metrics_date': metrics_period
            }
        except Exception as e:
            logger.error(f"Error calculating financial health for user {self.user_id}: {str(e)}")
            raise BusinessMetricsError(f"Failed to calculate financial health: {str(e)}")
    
    def _get_revenue_metrics(self, start_date, end_date):
        """Calculate revenue-related metrics."""
        # Get total revenue for the period
        revenue = db.session.query(
            func.sum(Order.total_amount)
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.order_date.between(start_date, end_date)
        ).scalar() or 0

        # Get revenue by product category
        revenue_by_category = dict(db.session.query(
            Product.category,
            func.sum(OrderItem.quantity * OrderItem.unit_price)
        ).join(
            OrderItem, OrderItem.product_id == Product.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.order_date.between(start_date, end_date)
        ).group_by(Product.category).all())

        # Calculate revenue growth vs previous period
        prev_period_end = start_date - timedelta(days=1)
        prev_period_start = prev_period_end - (end_date - start_date)
        
        prev_revenue = db.session.query(
            func.sum(Order.total_amount)
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.order_date.between(prev_period_start, prev_period_end)
        ).scalar() or 0

        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

        source_breakdown = self._get_revenue_breakdown(start_date, end_date)

        return {
            'total_revenue': float(revenue),
            'revenue_growth': round(revenue_growth, 2),
            'revenue_by_category': revenue_by_category,
            'average_order_value': self._calculate_avg_order_value(start_date, end_date),
            'recurring_revenue': self._calculate_recurring_revenue(start_date, end_date),
            'customer_count': self._get_customer_count(start_date, end_date),
            'source_breakdown': source_breakdown
        }

    def _get_revenue_breakdown(self, start_date, end_date) -> Dict[str, Dict[str, Any]]:
        """Return revenue order count and customer count breakdown by source."""
        breakdown = {
            'manual': {'revenue': 0.0, 'orders': 0, 'customers': 0},
            'storefront': {'revenue': 0.0, 'orders': 0, 'customers': 0}
        }

        try:
            order_source = func.coalesce(Order.source, Order.SOURCE_MANUAL).label('order_source')
            query = db.session.query(
                order_source,
                func.coalesce(func.sum(Order.total_amount), 0).label('total_revenue'),
                func.count(Order.id).label('order_count'),
                func.coalesce(func.count(func.distinct(Order.customer_id)), 0).label('customer_count')
            ).filter(
                Order.user_id == self.user_id,
                Order.status == 'completed',
                Order.order_date.between(start_date, end_date)
            ).group_by(order_source)

            results = query.all()
            for row in results:
                source_key = self._normalize_source_key(row.order_source)
                breakdown[source_key] = {
                    'revenue': float(row.total_revenue or 0.0),
                    'orders': int(row.order_count or 0),
                    'customers': int(row.customer_count or 0)
                }
        except Exception as exc:
            logger.error(f"Failed to calculate revenue breakdown by source: {exc}")

        combined = {
            'revenue': sum(source_info['revenue'] for source_info in breakdown.values()),
            'orders': sum(source_info['orders'] for source_info in breakdown.values()),
            'customers': sum(source_info['customers'] for source_info in breakdown.values())
        }

        return {
            'manual': breakdown['manual'],
            'storefront': breakdown['storefront'],
            'combined': combined
        }

    @staticmethod
    def _normalize_source_key(value: Any) -> str:
        """Normalize order source values into manual/storefront keys."""
        key = str(value or Order.SOURCE_MANUAL).strip().lower()
        return key if key in ('manual', 'storefront') else 'manual'

    def _get_expense_metrics(self, start_date, end_date):
        """Calculate expense-related metrics."""
        # Get all expenses for the period
        expenses = db.session.query(
            CostEntry.cost_type,
            func.sum(CostEntry.amount).label('total_amount')
        ).filter(
            CostEntry.user_id == self.user_id,
            CostEntry.date.between(start_date, end_date)
        ).group_by(CostEntry.cost_type).all()
        
        total_expenses = sum(expense.total_amount for expense in expenses)
        
        # Categorize expenses
        expense_categories = {
            'fixed': 0,
            'variable': 0,
            'operating': 0,
            'other': 0
        }
        
        for expense in expenses:
            # Map cost types to categories
            if expense.cost_type in [CostTypeEnum.RENT, CostTypeEnum.SALARIES, CostTypeEnum.INSURANCE]:
                expense_categories['fixed'] += expense.total_amount
            elif expense.cost_type in [CostTypeEnum.RAW_MATERIALS, CostTypeEnum.DIRECT_LABOR, CostTypeEnum.PACKAGING]:
                expense_categories['variable'] += expense.total_amount
            elif expense.cost_type in [CostTypeEnum.UTILITIES, CostTypeEnum.SOFTWARE, CostTypeEnum.MARKETING, CostTypeEnum.PROFESSIONAL_FEES]:
                expense_categories['operating'] += expense.total_amount
            else:
                expense_categories['other'] += expense.total_amount
        
        return {
            'total_expenses': float(total_expenses) if total_expenses else 0,
            'expense_categories': expense_categories,
            'expense_breakdown': [
                {'category': str(expense.cost_type.value), 'amount': float(expense.total_amount)}
                for expense in expenses
            ]
        }

    def _get_profitability_metrics(self, revenue_metrics, expense_metrics, start_date, end_date):
        """Calculate profitability metrics."""
        revenue = revenue_metrics.get('total_revenue', 0)
        total_expenses = expense_metrics.get('total_expenses', 0)
        # Ensure cogs is a float to avoid Decimal type mismatch
        cogs = float(sum(v for k, v in expense_metrics.get('expense_categories', {}).items() 
                        if k in ['variable']))

        overhead_expenses = max(float(total_expenses) - cogs, 0.0)
        
        gross_profit = revenue - cogs
        operating_profit = gross_profit - (total_expenses - cogs)
        net_profit = operating_profit  # Assuming no taxes/interest for now

        source_breakdown = self._get_source_profitability_breakdown(
            start_date=start_date,
            end_date=end_date,
            overhead_expenses=overhead_expenses
        )
        
        return {
            'gross_profit': float(gross_profit),
            'gross_margin': (gross_profit / revenue * 100) if revenue > 0 else 0,
            'operating_profit': float(operating_profit),
            'operating_margin': (operating_profit / revenue * 100) if revenue > 0 else 0,
            'net_profit': float(net_profit),
            'net_margin': (net_profit / revenue * 100) if revenue > 0 else 0,
            'roi': self._calculate_roi(revenue, total_expenses),
            'break_even_point': self._calculate_break_even(revenue, total_expenses),
            'source_breakdown': source_breakdown
        }

    def _get_source_profitability_breakdown(
        self,
        start_date: datetime,
        end_date: datetime,
        overhead_expenses: float = 0.0
    ) -> Dict[str, Dict[str, Any]]:
        """Return profitability metrics split by order source."""
        source_totals = {
            'manual': {'revenue': 0.0, 'subtotal': 0.0, 'tax': 0.0, 'orders': 0, 'gross_profit': 0.0},
            'storefront': {'revenue': 0.0, 'subtotal': 0.0, 'tax': 0.0, 'orders': 0, 'gross_profit': 0.0}
        }

        try:
            order_source = func.coalesce(Order.source, Order.SOURCE_MANUAL).label('order_source')
            revenue_rows = db.session.query(
                order_source,
                func.coalesce(func.sum(Order.total_amount), 0).label('total_revenue'),
                func.coalesce(func.sum(Order.subtotal), 0).label('subtotal_revenue'),
                func.coalesce(func.sum(Order.tax_amount), 0).label('tax_collected'),
                func.count(Order.id).label('order_count')
            ).filter(
                Order.user_id == self.user_id,
                Order.status == Order.STATUS_COMPLETED,
                Order.order_date.between(start_date, end_date)
            ).group_by(order_source).all()

            for row in revenue_rows:
                source_key = self._normalize_source_key(row.order_source)
                source_totals[source_key].update({
                    'revenue': float(row.total_revenue or 0.0),
                    'subtotal': float(row.subtotal_revenue or 0.0),
                    'tax': float(row.tax_collected or 0.0),
                    'orders': int(row.order_count or 0)
                })

            gross_rows = db.session.query(
                order_source,
                func.coalesce(
                    func.sum(
                        OrderItem.subtotal - (OrderItem.quantity * Product.cogs_per_unit)
                    ),
                    0
                ).label('gross_profit')
            ).join(
                Order, Order.id == OrderItem.order_id
            ).join(
                Product, Product.id == OrderItem.product_id
            ).filter(
                Order.user_id == self.user_id,
                Order.status == Order.STATUS_COMPLETED,
                Order.order_date.between(start_date, end_date)
            ).group_by(order_source).all()

            for row in gross_rows:
                source_key = self._normalize_source_key(row.order_source)
                source_totals[source_key]['gross_profit'] = float(row.gross_profit or 0.0)

        except Exception as exc:
            logger.error(f"Failed to calculate source profitability breakdown: {exc}")

        total_revenue = sum(data['revenue'] for data in source_totals.values())
        normalized_overhead = max(float(overhead_expenses or 0.0), 0.0)
        breakdown: Dict[str, Dict[str, Any]] = {}

        for source_key, data in source_totals.items():
            revenue = float(data.get('revenue', 0.0) or 0.0)
            gross_profit = float(data.get('gross_profit', 0.0) or 0.0)
            allocated_overhead = (normalized_overhead * (revenue / total_revenue)) if total_revenue > 0 else 0.0
            net_profit = gross_profit - allocated_overhead
            orders = int(data.get('orders', 0) or 0)

            breakdown[source_key] = {
                'revenue': revenue,
                'subtotal': float(data.get('subtotal', 0.0) or 0.0),
                'tax': float(data.get('tax', 0.0) or 0.0),
                'orders': orders,
                'avg_order_value': (revenue / orders) if orders > 0 else 0.0,
                'gross_profit': gross_profit,
                'gross_margin': (gross_profit / revenue * 100) if revenue > 0 else 0.0,
                'allocated_overhead': allocated_overhead,
                'net_profit': net_profit,
                'net_margin': (net_profit / revenue * 100) if revenue > 0 else 0.0
            }

        combined_revenue = breakdown['manual']['revenue'] + breakdown['storefront']['revenue']
        combined_orders = breakdown['manual']['orders'] + breakdown['storefront']['orders']
        combined_gross = breakdown['manual']['gross_profit'] + breakdown['storefront']['gross_profit']
        combined_net = breakdown['manual']['net_profit'] + breakdown['storefront']['net_profit']

        breakdown['combined'] = {
            'revenue': combined_revenue,
            'subtotal': breakdown['manual']['subtotal'] + breakdown['storefront']['subtotal'],
            'tax': breakdown['manual']['tax'] + breakdown['storefront']['tax'],
            'orders': combined_orders,
            'avg_order_value': (combined_revenue / combined_orders) if combined_orders > 0 else 0.0,
            'gross_profit': combined_gross,
            'gross_margin': (combined_gross / combined_revenue * 100) if combined_revenue > 0 else 0.0,
            'allocated_overhead': breakdown['manual']['allocated_overhead'] + breakdown['storefront']['allocated_overhead'],
            'net_profit': combined_net,
            'net_margin': (combined_net / combined_revenue * 100) if combined_revenue > 0 else 0.0
        }

        return breakdown

    def _get_cash_flow_metrics(self, start_date, end_date):
        """Calculate cash flow metrics."""
        # Get cash inflows (completed orders)
        cash_in = db.session.query(
            func.sum(Order.total_amount)
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.payment_status == 'paid',
            Order.order_date.between(start_date, end_date)
        ).scalar() or 0
        
        # Get cash outflows (expenses)
        cash_out = db.session.query(
            func.sum(CostEntry.amount)
        ).filter(
            CostEntry.user_id == self.user_id,
            CostEntry.date.between(start_date, end_date)
        ).scalar() or 0
        
        # Ensure proper float conversion to avoid Decimal type issues
        cash_in = float(cash_in)
        cash_out = float(cash_out)
        
        operating_cash_flow = cash_in - cash_out
        
        # Simple cash burn rate (monthly)
        days_in_period = (end_date - start_date).days or 30
        monthly_burn_rate = (cash_out / days_in_period) * 30
        
        # Calculate runway (months of cash left)
        current_cash = self._get_current_cash_balance()
        runway = (current_cash / monthly_burn_rate) if monthly_burn_rate > 0 else 0
        
        return {
            'operating_cash_flow': float(operating_cash_flow),
            'cash_in': float(cash_in),
            'cash_out': float(cash_out),
            'cash_burn_rate': float(monthly_burn_rate),
            'runway': round(runway, 1)  # in months
        }

    def get_cash_flow_trends(
        self,
        months: int = 6,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Return monthly cash flow trends (cash in, cash out, operating cash flow)."""
        if months < 1:
            months = 1
        if end_date is None:
            end_date = datetime.utcnow()

        current_month_start = end_date.replace(day=1)
        start_month = self._adjust_month(current_month_start, -(months - 1))

        trends: List[Dict[str, Any]] = []
        current = start_month

        for _ in range(months):
            next_month = self._adjust_month(current, 1)
            month_end = next_month - timedelta(days=1)
            if current == current_month_start:
                month_end = end_date

            cash_metrics = self._get_cash_flow_metrics(current, month_end)
            trends.append({
                'label': current.strftime('%b %Y'),
                'month': current.strftime('%Y-%m'),
                'cash_in': cash_metrics.get('cash_in', 0),
                'cash_out': cash_metrics.get('cash_out', 0),
                'operating_cash_flow': cash_metrics.get('operating_cash_flow', 0)
            })

            current = next_month

        return trends

    def _get_working_capital_metrics(self):
        """Calculate working capital metrics."""
        # Get current assets (cash + accounts receivable + inventory)
        current_assets = self._get_current_assets()
        
        # Get current liabilities (accounts payable + short-term debt)
        current_liabilities = self._get_current_liabilities()
        
        working_capital = current_assets - current_liabilities
        
        # Quick ratio (current assets - inventory) / current liabilities
        inventory_value = self._get_inventory_value()
        quick_assets = current_assets - inventory_value
        quick_ratio = (quick_assets / current_liabilities) if current_liabilities > 0 else 0
        
        # Current ratio
        current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else 0
        
        return {
            'current_assets': float(current_assets),
            'current_liabilities': float(current_liabilities),
            'working_capital': float(working_capital),
            'current_ratio': round(current_ratio, 2),
            'quick_ratio': round(quick_ratio, 2),
            'inventory_turnover': self._calculate_inventory_turnover(),
            'days_sales_outstanding': self._calculate_days_sales_outstanding()
        }

    # Helper methods
    def _to_decimal(self, value: Any) -> Decimal:
        """Normalize numeric results to Decimal to avoid mixed-type arithmetic."""
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            logger.warning(f"Failed to convert value to Decimal: {value} ({exc})")
            return Decimal('0')
    def _calculate_avg_order_value(self, start_date, end_date):
        """Calculate average order value for the period."""
        result = db.session.query(
            func.count(Order.id),
            func.sum(Order.total_amount)
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.order_date.between(start_date, end_date)
        ).first()
        
        order_count, total_amount = result or (0, 0)
        return float(total_amount / order_count) if order_count > 0 else 0

    def _calculate_recurring_revenue(self, start_date, end_date):
        """Calculate monthly recurring revenue (MRR)."""
        # This is a simplified version - you might want to enhance this based on your subscription model
        mrr = db.session.query(
            func.sum(Order.total_amount)
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.is_recurring == True,  # noqa: E712
            Order.order_date.between(start_date, end_date)
        ).scalar() or 0
        
        return float(mrr)

    def _calculate_roi(self, revenue, expenses):
        """Calculate return on investment."""
        # This is a simplified ROI calculation
        # You might want to customize this based on your business model
        return ((revenue - expenses) / expenses * 100) if expenses > 0 else 0

    def _calculate_break_even(self, revenue, expenses):
        """Calculate break-even point."""
        # This is a simplified break-even calculation
        # You might want to enhance this with more sophisticated logic
        return revenue - expenses

    def _get_current_assets(self):
        """Get total current assets."""
        try:
            # Cash balance (simplified - could be from bank accounts)
            cash_balance = self._get_cash_balance()
            
            # Accounts receivable (unpaid orders)
            accounts_receivable = self._get_accounts_receivable()
            
            # Inventory value
            inventory_value = self._get_inventory_value()
            
            # Total current assets
            current_assets = cash_balance + accounts_receivable + inventory_value
            
            return float(current_assets)
        except Exception as e:
            logger.error(f"Error calculating current assets: {e}")
            return 0.0

    def _get_current_liabilities(self):
        """Get total current liabilities."""
        try:
            # Accounts payable (unpaid costs/expenses)
            accounts_payable = self._get_accounts_payable()
            
            # Short-term debt (could be implemented later)
            short_term_debt = 0.0
            
            # Total current liabilities
            current_liabilities = accounts_payable + short_term_debt
            
            return float(current_liabilities)
        except Exception as e:
            logger.error(f"Error calculating current liabilities: {e}")
            return 0.0

    def _get_cash_balance(self):
        """Get cash balance from business operations."""
        try:
            # Calculate cash balance from profit and loss
            # This is a simplified calculation - in real systems this would come from bank accounts
            current_month = datetime.utcnow().replace(day=1)
            
            # Get cash inflows (revenue)
            cash_in_result = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
                .filter(Order.user_id == self.user_id,
                       Order.status != 'cancelled',
                       Order.created_at >= current_month).scalar()
            cash_in = self._to_decimal(cash_in_result)
            
            # Get cash outflows (costs)
            cash_out_result = db.session.query(func.coalesce(func.sum(CostEntry.amount), 0))\
                .filter(CostEntry.user_id == self.user_id,
                       CostEntry.date >= current_month).scalar()
            cash_out = self._to_decimal(cash_out_result)
            
            # Net cash position
            cash_balance = cash_in - cash_out
            
            return float(max(cash_balance, Decimal('0')))  # Don't show negative cash balance
        except Exception as e:
            logger.error(f"Error calculating cash balance: {e}")
            return 0.0

    def _get_accounts_receivable(self):
        """Get total accounts receivable (unpaid orders)."""
        try:
            # Get orders that are not paid yet
            unpaid_amount = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
                .filter(Order.user_id == self.user_id,
                       Order.status.in_(['pending', 'processing']),
                       Order.payment_status != 'paid').scalar() or 0.0
            
            return float(unpaid_amount)
        except Exception as e:
            logger.error(f"Error calculating accounts receivable: {e}")
            return 0.0

    def _get_accounts_payable(self):
        """Get total accounts payable (unpaid costs/expenses)."""
        try:
            current_month = datetime.utcnow().replace(day=1)
        
            # Query total monthly costs
            result = db.session.query(
                func.coalesce(func.sum(CostEntry.amount), 0)
            ).filter(
                CostEntry.user_id == self.user_id,
                CostEntry.date >= current_month
            ).scalar()
        
            # Convert result to Decimal safely
            if result is None or result == 0:
                total_monthly_costs = Decimal('0')
            else:
                total_monthly_costs = Decimal(str(result))  # str() avoids float precision issues
        
            # Estimate unpaid as 30% (adjust as needed)
            estimated_unpaid = total_monthly_costs * Decimal('0.3')
        
            return float(estimated_unpaid)
        except Exception as e:
            logger.error(f"Error calculating accounts payable: {e}")
            return 0.0

    
    def _get_inventory_value(self):
        """Get total inventory value."""
        from app.models.products import Product

        # Get all products with their current stock and cost
        products = Product.query.filter_by(user_id=self.user_id).all()
        total_value = sum(float(product.cogs_per_unit) * product.current_stock for product in products)
        return total_value

    def _calculate_inventory_turnover(self):
        """Calculate inventory turnover ratio."""
        # This should be implemented based on your inventory system
        return 0.0

    def _calculate_days_sales_outstanding(self):
        """Calculate days sales outstanding (DSO)."""
        # This should be implemented based on your accounting system
        return 0.0

    def get_category_breakdown(self):
        """
        Get revenue breakdown by product category.
        """
        try:
            results = (
                db.session.query(
                    Product.category,
                    func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")
                )
                .join(OrderItem, OrderItem.product_id == Product.id)
                .join(Order, Order.id == OrderItem.order_id)
                .filter(
                    Order.user_id == self.user_id,
                    Order.status == "completed"
                )
                .group_by(Product.category)
                .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
                .all()
            )

            return [
                {
                    "category": r.category or 'Uncategorized',
                    "revenue": float(r.revenue or 0)
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting category breakdown: {e}")
            return []

    def get_sales_funnel(self):
        """
        Get sales funnel data (visitors -> cart adds -> checkouts -> purchases).
        """
        try:
            # This is a simplified version - you might want to enhance with actual tracking
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            # Get completed orders (purchases)
            purchases = db.session.query(func.count(Order.id)).filter(
                Order.user_id == self.user_id,
                Order.status == "completed",
                Order.order_date.between(start_date, end_date)
            ).scalar() or 0
            
            # Get orders with items (checkouts) - simplified
            checkouts = db.session.query(func.count(func.distinct(Order.id))).filter(
                Order.user_id == self.user_id,
                Order.order_date.between(start_date, end_date)
            ).scalar() or 0
            
            # For demo purposes, estimate cart adds and visitors
            # In a real app, you'd track these with analytics
            cart_adds = max(checkouts * 2, purchases * 3)
            visitors = max(cart_adds * 3, purchases * 10)
            
            return {
                'visitors': visitors,
                'cart_adds': cart_adds,
                'checkouts': checkouts,
                'purchases': purchases
            }
        except Exception as e:
            logger.error(f"Error getting sales funnel: {e}")
            return {
                'visitors': 0,
                'cart_adds': 0,
                'checkouts': 0,
                'purchases': 0
            }

    def _get_customer_count(self, start_date, end_date):
        """Get count of unique customers in the period."""
        return db.session.query(
            func.count(func.distinct(Order.customer_id))
        ).filter(
            Order.user_id == self.user_id,
            Order.status == 'completed',
            Order.order_date.between(start_date, end_date)
        ).scalar() or 0

    def _get_current_cash_balance(self):
        """Get current cash balance."""
        try:
            # Calculate current cash balance from business operations
            # This is the cumulative cash position from all time
            cash_in_result = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
                .filter(Order.user_id == self.user_id,
                       Order.status == 'completed',
                       Order.payment_status == 'paid').scalar()
            cash_in = self._to_decimal(cash_in_result)
            
            cash_out_result = db.session.query(func.coalesce(func.sum(CostEntry.amount), 0))\
                .filter(CostEntry.user_id == self.user_id).scalar()
            cash_out = self._to_decimal(cash_out_result)
            
            cash_balance = cash_in - cash_out
            return float(max(cash_balance, Decimal('0')))  # Don't show negative cash
        except Exception as e:
            logger.error(f"Error calculating current cash balance: {e}")
            return 0.0
        
    def _adjust_month(self, source: datetime, offset: int) -> datetime:
        """Return a datetime adjusted by a given number of full months."""
        month_index = (source.month - 1) + offset
        year = source.year + (month_index // 12)
        month = (month_index % 12) + 1
        return source.replace(year=year, month=month, day=1)
        
    def get_top_products(self, limit: int = 10):
        """Return top products by revenue."""
        results = (
            db.session.query(
                Product.id.label('id'),
                Product.name.label('name'),
                Product.category.label('category'),
                func.sum(OrderItem.quantity).label('units'),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue')
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.user_id == self.user_id, Order.status == 'completed')
            .group_by(Product.id, Product.name, Product.category)
            .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                'id': r.id,
                'name': r.name,
                'category': r.category or 'Uncategorized',
                'units_sold': int(r.units or 0),
                'revenue': float(r.revenue or 0)
            }
            for r in results
        ]

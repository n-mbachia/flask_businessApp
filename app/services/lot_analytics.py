# app/services/lot_analytics.py

from datetime import datetime, timedelta, date
from sqlalchemy import func, exc, and_
from app import db, cache
from app.models import InventoryLot, Product, OrderItem, Order
from typing import Dict, Any, Optional, List, Tuple
import logging
import time

logger = logging.getLogger(__name__)

class AnalyticsError(Exception):
    pass

class LotAnalytics:
    CACHE_TIMEOUT = 3600
    MAX_QUERY_RETRIES = 3
    RETRY_DELAY = 1

    @staticmethod
    def _retry_query(query_func, max_retries=MAX_QUERY_RETRIES):
        for attempt in range(max_retries):
            try:
                return query_func()
            except exc.SQLAlchemyError as e:
                if attempt == max_retries - 1:
                    logger.exception("Database query failed")
                    raise AnalyticsError("Database query failed") from e
                time.sleep((attempt + 1) * LotAnalytics.RETRY_DELAY)
        raise AnalyticsError("Unexpected error in query retry logic")

    @staticmethod
    @cache.memoize(timeout=CACHE_TIMEOUT)
    def get_lot_performance(lot_id: int) -> Dict[str, Any]:
        """Get performance metrics for a single lot."""
        try:
            lot = InventoryLot.query.options(
                db.joinedload(InventoryLot.product)
            ).get_or_404(lot_id)

            sales_data = db.session.query(
                func.coalesce(func.sum(OrderItem.quantity), 0).label('total_units_sold'),
                func.coalesce(func.sum(OrderItem.subtotal), 0).label('total_revenue'),
                func.min(Order.order_date).label('first_sale_date')
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                OrderItem.lot_id == lot_id,
                Order.status == 'completed'
            ).first()

            total_units_sold = int(sales_data.total_units_sold or 0)
            total_revenue = float(sales_data.total_revenue or 0)
            first_sale_date = sales_data.first_sale_date

            remaining_units = max(0, lot.quantity_received - total_units_sold)
            sell_through_rate = (total_units_sold / lot.quantity_received * 100) if lot.quantity_received > 0 else 0
            avg_price_per_unit = (total_revenue / total_units_sold) if total_units_sold > 0 else 0

            current_date = datetime.utcnow().date()
            lot_age_days = (current_date - lot.received_date).days if lot.received_date else 0

            daily_sales_rate = total_units_sold / lot_age_days if lot_age_days > 0 else 0
            days_of_inventory = (remaining_units / daily_sales_rate) if daily_sales_rate > 0 else float('inf')

            return {
                'lot_id': lot_id,
                'product_id': lot.product_id,
                'product_name': lot.product.name if lot.product else 'Unknown',
                'initial_quantity': lot.quantity_received,
                'remaining_quantity': remaining_units,
                'total_units_sold': total_units_sold,
                'total_revenue': total_revenue,
                'sell_through_rate': sell_through_rate,
                'average_price_per_unit': avg_price_per_unit,
                'lot_age_days': lot_age_days,
                'days_of_inventory': days_of_inventory,
                'first_sale_date': first_sale_date.isoformat() if first_sale_date else None,
                'received_date': lot.received_date.isoformat() if lot.received_date else None,
                'expiration_date': lot.expiration_date.isoformat() if lot.expiration_date else None,
                'created_at': lot.created_at.isoformat() if lot.created_at else None,
                'updated_at': lot.updated_at.isoformat() if lot.updated_at else None
            }
        except Exception as e:
            logger.exception(f"Error getting lot performance for lot {lot_id}")
            raise AnalyticsError(f"Failed to get lot performance: {str(e)}")

    @classmethod
    def get_lots_performance_summary(cls, user_id: int, product_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get performance summary for all lots (optionally filtered by product).
        Requires user_id to filter by ownership.
        """
        try:
            query = db.session.query(
                InventoryLot.id.label('lot_id'),
                InventoryLot.lot_number.label('lot_number'),
                InventoryLot.cost_per_unit.label('unit_cost'),
                InventoryLot.created_at.label('created_at'),
                Product.id.label('product_id'),
                Product.name.label('product_name'),
                InventoryLot.quantity_received.label('initial_quantity'),
                InventoryLot.received_date,
                InventoryLot.expiration_date,
                func.coalesce(
                    db.session.query(func.sum(OrderItem.quantity))
                    .join(Order, Order.id == OrderItem.order_id)
                    .filter(
                        OrderItem.lot_id == InventoryLot.id,
                        Order.status == 'completed'
                    )
                    .scalar_subquery(), 0
                ).label('units_sold'),
                func.coalesce(
                    db.session.query(func.sum(OrderItem.subtotal))
                    .join(Order, Order.id == OrderItem.order_id)
                    .filter(
                        OrderItem.lot_id == InventoryLot.id,
                        Order.status == 'completed'
                    )
                    .scalar_subquery(), 0
                ).label('revenue')
            ).join(
                Product, Product.id == InventoryLot.product_id
            ).filter(
                Product.user_id == user_id
            )

            if product_id is not None:
                query = query.filter(InventoryLot.product_id == product_id)

            results = query.order_by(InventoryLot.received_date.desc()).all()

            lots = []
            total_initial_quantity = 0
            total_units_sold = 0
            total_revenue = 0

            today = date.today()
            for row in results:
                initial_quantity = row.initial_quantity or 0
                units_sold = row.units_sold or 0
                revenue = float(row.revenue or 0)
                remaining_quantity = max(initial_quantity - units_sold, 0)
                sell_through_rate = (
                    (units_sold / initial_quantity * 100) if initial_quantity > 0 else 0.0
                )
                unit_cost = float(row.unit_cost or 0)
                cost_total = units_sold * unit_cost
                gross_margin = (
                    ((revenue - cost_total) / revenue * 100) if revenue > 0 else 0.0
                )

                expiration_status = 'good'
                if row.expiration_date:
                    days_until_expiry = (row.expiration_date - today).days
                    if days_until_expiry < 0:
                        expiration_status = 'expired'
                    elif days_until_expiry < 30:
                        expiration_status = 'critical'

                status = 'active'
                if remaining_quantity <= 0:
                    status = 'sold_out'
                elif expiration_status == 'expired':
                    status = 'inactive'
                elif remaining_quantity < initial_quantity:
                    status = 'partial'

                days_since_received = None
                if row.received_date:
                    days_since_received = (today - row.received_date).days

                lot_data = {
                    'lot_id': row.lot_id,
                    'lot_number': row.lot_number,
                    'product_id': row.product_id,
                    'product_name': row.product_name,
                    'initial_quantity': initial_quantity,
                    'received_date': row.received_date.isoformat() if row.received_date else None,
                    'expiration_date': row.expiration_date.isoformat() if row.expiration_date else None,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'units_sold': units_sold,
                    'revenue': revenue,
                    'remaining_quantity': remaining_quantity,
                    'sell_through_rate': round(sell_through_rate, 2),
                    'gross_margin': round(gross_margin, 2),
                    'unit_cost': unit_cost,
                    'status': status,
                    'expiration_status': expiration_status,
                    'days_since_received': days_since_received
                }
                lots.append(lot_data)

                total_initial_quantity += row.initial_quantity
                total_units_sold += row.units_sold
                total_revenue += float(row.revenue)

            overall_sell_through = (
                (total_units_sold / total_initial_quantity * 100) if total_initial_quantity > 0 else 0
            )

            return {
                'lots': lots,
                'summary': {
                    'total_lots': len(lots),
                    'total_initial_quantity': total_initial_quantity,
                    'total_units_sold': total_units_sold,
                    'total_remaining': total_initial_quantity - total_units_sold,
                    'total_revenue': total_revenue,
                    'overall_sell_through_rate': overall_sell_through,
                    'average_revenue_per_lot': total_revenue / len(lots) if lots else 0
                }
            }
        except Exception as e:
            logger.exception("Error getting lots performance summary")
            raise AnalyticsError(f"Failed to get lots performance summary: {str(e)}")

    @classmethod
    def get_lot_aging_report(cls, user_id: int) -> Dict[str, Any]:
        """Generate aging report for lots based on expiration dates."""
        try:
            today = datetime.utcnow().date()
            thirty_days = today + timedelta(days=30)
            ninety_days = today + timedelta(days=90)

            # Subquery for units sold per lot
            units_sold_subq = db.session.query(
                OrderItem.lot_id,
                func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold')
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.status == 'completed'
            ).group_by(OrderItem.lot_id).subquery()

            # Subquery for revenue per lot
            revenue_subq = db.session.query(
                OrderItem.lot_id,
                func.coalesce(func.sum(OrderItem.subtotal), 0).label('revenue')
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.status == 'completed'
            ).group_by(OrderItem.lot_id).subquery()

            query = db.session.query(
                InventoryLot.id.label('lot_id'),
                Product.id.label('product_id'),
                Product.name.label('product_name'),
                InventoryLot.quantity_received.label('initial_quantity'),
                InventoryLot.received_date,
                InventoryLot.expiration_date,
                (today - InventoryLot.received_date).days.label('age_days'),
                func.coalesce(units_sold_subq.c.units_sold, 0).label('units_sold'),
                func.coalesce(revenue_subq.c.revenue, 0).label('revenue'),
                (InventoryLot.quantity_received - func.coalesce(units_sold_subq.c.units_sold, 0)).label('remaining_quantity'),
                func.case(
                    (InventoryLot.expiration_date < today, 'Expired'),
                    (InventoryLot.expiration_date <= thirty_days, 'Expiring Soon (0-30 days)'),
                    (InventoryLot.expiration_date <= ninety_days, 'Expiring (31-90 days)'),
                    else_='Good (90+ days)'
                ).label('expiry_status')
            ).outerjoin(
                units_sold_subq, units_sold_subq.c.lot_id == InventoryLot.id
            ).outerjoin(
                revenue_subq, revenue_subq.c.lot_id == InventoryLot.id
            ).join(
                Product, Product.id == InventoryLot.product_id
            ).filter(
                Product.user_id == user_id
            ).order_by(
                func.case(
                    (InventoryLot.expiration_date < today, 1),
                    (InventoryLot.expiration_date <= thirty_days, 2),
                    (InventoryLot.expiration_date <= ninety_days, 3),
                    else_=4
                ),
                InventoryLot.expiration_date
            ).all()

            lots = []
            summary = {'total_lots': 0, 'expired': 0, 'expiring_soon': 0, 'expiring': 0, 'good': 0}

            for row in query:
                lot_data = {
                    'lot_id': row.lot_id,
                    'product_id': row.product_id,
                    'product_name': row.product_name,
                    'initial_quantity': row.initial_quantity,
                    'received_date': row.received_date.isoformat() if row.received_date else None,
                    'expiration_date': row.expiration_date.isoformat() if row.expiration_date else None,
                    'age_days': row.age_days,
                    'units_sold': row.units_sold,
                    'remaining_quantity': row.remaining_quantity,
                    'revenue': float(row.revenue),
                    'expiry_status': row.expiry_status
                }
                lots.append(lot_data)
                summary['total_lots'] += 1
                if row.expiry_status == 'Expired':
                    summary['expired'] += 1
                elif 'Expiring Soon' in row.expiry_status:
                    summary['expiring_soon'] += 1
                elif 'Expiring (' in row.expiry_status:
                    summary['expiring'] += 1
                else:
                    summary['good'] += 1

            return {'lots': lots, 'summary': summary}
        except Exception as e:
            logger.exception("Error generating lot aging report")
            raise AnalyticsError(f"Failed to generate lot aging report: {str(e)}")

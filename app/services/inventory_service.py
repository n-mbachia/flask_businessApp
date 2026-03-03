"""
Inventory Service

This module provides services for inventory management operations,
using inventory movements as the single source of truth for stock levels.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import Session, joinedload
import logging

from app.models import Product, InventoryLog
from app import db

logger = logging.getLogger(__name__)


class InventoryError(Exception):
    """Custom exception for inventory-related errors."""
    pass


class ValidationError(InventoryError):
    """Exception raised for validation errors."""
    pass


class InventoryService:
    """Service class for inventory-related operations."""

    @staticmethod
    def get_inventory_summary(db_session: Session, user_id: int) -> Dict[str, Any]:
        """
        Get a summary of the user's inventory.
        Uses subqueries to compute current stock from inventory logs.

        Args:
            db_session: Database session
            user_id: ID of the user

        Returns:
            Dict containing inventory summary
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("Invalid user ID")

        try:
            # Subquery to compute current stock for each product
            stock_subq = (
                db_session.query(
                    InventoryLog.product_id,
                    func.coalesce(func.sum(InventoryLog.quantity_change), 0).label('current_stock')
                )
                .join(Product, InventoryLog.product_id == Product.id)
                .filter(Product.user_id == user_id)
                .group_by(InventoryLog.product_id)
                .subquery()
            )

            summary = (
                db_session.query(
                    func.count(Product.id).label('total_items'),
                    func.coalesce(
                        func.sum(
                            case(
                                (stock_subq.c.current_stock <= Product.reorder_level, 1),
                                else_=0
                            )
                        ), 0
                    ).label('low_stock_items'),
                    func.coalesce(
                        func.sum(
                            case(
                                (stock_subq.c.current_stock <= 0, 1),
                                else_=0
                            )
                        ), 0
                    ).label('out_of_stock_items'),
                    func.coalesce(
                        func.sum(stock_subq.c.current_stock * Product.selling_price_per_unit), 0
                    ).label('total_value')
                )
                .outerjoin(stock_subq, Product.id == stock_subq.c.product_id)
                .filter(Product.user_id == user_id, Product.is_active == True)
                .first()
            )

            return {
                'total_items': summary.total_items or 0,
                'low_stock_items': summary.low_stock_items or 0,
                'out_of_stock_items': summary.out_of_stock_items or 0,
                'total_value': float(summary.total_value or 0)
            }
        except Exception as e:
            logger.error(f"Database error in get_inventory_summary: {str(e)}")
            raise InventoryError(f"Failed to get inventory summary: {str(e)}")

    @classmethod
    def update_inventory_levels(
        cls,
        db_session: Session,
        user_id: int,
        updates: List[Dict[str, Any]],
        reference_type: str = 'order',
        reference_id: int = None,
        notes: str = None,
        auto_commit: bool = True
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Update inventory levels for multiple items by creating inventory logs.

        Args:
            db_session: Database session
            user_id: ID of the user
            updates: List of dicts with product_id, quantity_change, and optional unit_cost
            reference_type: Type of reference (order, return, adjustment, etc.)
            reference_id: ID of the reference document
            notes: Additional notes for the inventory log

        Returns:
            Tuple of (success: bool, results: List[Dict])
        """
        results = []

        try:
            for update in updates:
                product_id = update.get('product_id')
                quantity_change = float(update.get('quantity_change', 0))
                unit_cost = update.get('unit_cost')  # optional, for new purchases

                if not product_id:
                    results.append({
                        'success': False,
                        'message': 'Product ID is required',
                        'product_id': None
                    })
                    continue

                # Fetch product to verify ownership and get current stock via hybrid property
                product = db_session.query(Product).get(product_id)
                if not product or product.user_id != user_id:
                    results.append({
                        'success': False,
                        'message': f'Product not found or access denied: {product_id}',
                        'product_id': product_id
                    })
                    continue

                # Get current stock using the hybrid property (executes a query)
                current_stock = product.current_stock

                # Check for negative stock (unless it's a return/adjustment)
                new_stock = current_stock + quantity_change
                if new_stock < 0 and reference_type not in ('return', 'adjustment'):
                    results.append({
                        'success': False,
                        'message': f'Insufficient stock for {product.name}. Available: {current_stock}, Requested: {abs(quantity_change)}',
                        'product_id': product_id,
                        'available_quantity': current_stock,
                        'requested_quantity': abs(quantity_change)
                    })
                    continue

                # Create inventory log
                log = InventoryLog(
                    product_id=product_id,
                    user_id=user_id,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    quantity_change=quantity_change,
                    quantity_before=current_stock,
                    quantity_after=new_stock,
                    unit_cost=unit_cost if unit_cost is not None else product.cogs_per_unit,
                    notes=notes or f'Inventory updated via {reference_type} #{reference_id or "N/A"}'
                )
                db_session.add(log)

                results.append({
                    'success': True,
                    'product_id': product_id,
                    'product_name': product.name,
                    'old_quantity': current_stock,
                    'new_quantity': new_stock,
                    'quantity_change': quantity_change
                })

            if auto_commit:
                db_session.commit()
            else:
                db_session.flush()
            return True, results

        except Exception as e:
            db_session.rollback()
            logger.error(f"Inventory update failed: {str(e)}", exc_info=True)
            raise InventoryError(f'Failed to update inventory: {str(e)}')

    @staticmethod
    def validate_order_items(
        db_session: Session,
        user_id: int,
        items: List[Dict[str, Any]]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate if there's sufficient stock for order items using current_stock.

        Args:
            db_session: Database session
            user_id: ID of the user
            items: List of order items with product_id and quantity

        Returns:
            Tuple of (is_valid: bool, validation_results: List[Dict]]
        """
        if not items:
            return False, [{'success': False, 'message': 'No items provided'}]

        validation_results = []
        all_valid = True

        product_ids = [item.get('product_id') for item in items if item.get('product_id')]
        if not product_ids:
            return False, [{'success': False, 'message': 'No valid product IDs provided'}]

        # Fetch all products at once
        products = {
            p.id: p for p in db_session.query(Product).filter(
                Product.id.in_(product_ids),
                Product.user_id == user_id,
                Product.is_active == True
            ).all()
        }

        for item in items:
            product_id = item.get('product_id')
            try:
                quantity = Decimal(str(item.get('quantity', 0)))
            except (ValueError, TypeError):
                quantity = Decimal('0')

            if not product_id:
                validation_results.append({
                    'success': False,
                    'message': 'Product ID is required',
                    'product_id': None
                })
                all_valid = False
                continue

            product = products.get(product_id)
            if not product:
                validation_results.append({
                    'success': False,
                    'message': f'Product not found or access denied: {product_id}',
                    'product_id': product_id
                })
                all_valid = False
                continue

            # Get current stock via hybrid property (each call may query; consider optimizing with a pre-fetch)
            available = product.current_stock

            if quantity <= 0:
                validation_results.append({
                    'success': False,
                    'message': f'Invalid quantity for {product.name}. Quantity must be greater than 0',
                    'product_id': product_id,
                    'available_quantity': available,
                    'requested_quantity': quantity
                })
                all_valid = False
            elif available < quantity:
                validation_results.append({
                    'success': False,
                    'message': f'Insufficient stock for {product.name}. Available: {available}, Requested: {quantity}',
                    'product_id': product_id,
                    'available_quantity': available,
                    'requested_quantity': quantity,
                    'product_name': product.name,
                    'needs_more': float(quantity - available)
                })
                all_valid = False
            else:
                validation_results.append({
                    'success': True,
                    'message': 'Sufficient stock available',
                    'product_id': product_id,
                    'product_name': product.name,
                    'available_quantity': available,
                    'requested_quantity': quantity
                })

        return all_valid, validation_results

    @staticmethod
    def get_inventory_logs(
        db_session: Session,
        user_id: int,
        product_id: int = None,
        reference_type: str = None,
        reference_id: int = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get inventory logs with filtering options.

        Args:
            db_session: Database session
            user_id: ID of the user
            product_id: Filter by product ID
            reference_type: Filter by reference type (e.g., 'order', 'return')
            reference_id: Filter by reference ID
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            List of inventory log entries
        """
        query = db_session.query(InventoryLog).join(Product).filter(
            Product.user_id == user_id
        ).options(joinedload(InventoryLog.product))

        if product_id:
            query = query.filter(InventoryLog.product_id == product_id)
        if reference_type:
            query = query.filter(InventoryLog.reference_type == reference_type)
        if reference_id:
            query = query.filter(InventoryLog.reference_id == reference_id)

        logs = query.order_by(
            InventoryLog.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [{
            'id': log.id,
            'product_id': log.product_id,
            'product_name': log.product.name,
            'reference_type': log.reference_type,
            'reference_id': log.reference_id,
            'quantity_change': log.quantity_change,
            'quantity_before': log.quantity_before,
            'quantity_after': log.quantity_after,
            'unit_cost': float(log.unit_cost) if log.unit_cost else None,
            'notes': log.notes,
            'created_at': log.created_at.isoformat(),
            'user_id': log.user_id
        } for log in logs]

    @staticmethod
    def get_low_stock_items(
        db_session: Session,
        user_id: int,
        threshold: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get a list of items that are below the specified stock threshold.
        Uses a subquery to compute current stock from inventory logs.

        Args:
            db_session: Database session
            user_id: ID of the user
            threshold: Stock level threshold to consider as low (uses reorder_point if None)
            limit: Maximum number of items to return

        Returns:
            List of items below the threshold
        """
        # Subquery to compute current stock for each product
        stock_subq = (
            db_session.query(
                InventoryLog.product_id,
                func.coalesce(func.sum(InventoryLog.quantity_change), 0).label('current_stock')
            )
            .join(Product, InventoryLog.product_id == Product.id)
            .filter(Product.user_id == user_id)
            .group_by(InventoryLog.product_id)
            .subquery()
        )

        query = db_session.query(
            Product.id,
            Product.name,
            Product.sku,
            stock_subq.c.current_stock.label('current_stock'),
            Product.reorder_level,
            Product.selling_price_per_unit.label('price'),
            Product.category
        ).outerjoin(stock_subq, Product.id == stock_subq.c.product_id).filter(
            Product.user_id == user_id,
            Product.is_active == True
        )

        if threshold is not None:
            query = query.filter(stock_subq.c.current_stock <= threshold)
        else:
            query = query.filter(stock_subq.c.current_stock <= Product.reorder_level)

        products = query.order_by(stock_subq.c.current_stock.asc()).limit(limit).all()

        return [{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'current_stock': p.current_stock,
            'reorder_point': p.reorder_level,
            'price': float(p.price) if p.price else 0.0,
            'category': p.category
        } for p in products]

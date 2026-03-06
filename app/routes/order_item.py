"""
Order Item Management Blueprint

Handles CRUD operations for order items, including lot selection.
"""

from flask import (
    Blueprint, jsonify, request, current_app, flash, redirect, url_for, render_template
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import HTTPException
from decimal import Decimal
import json

from app import db
from app.models import Order, OrderItem, Product, Customer, InventoryLot
from app.forms.enhanced_order_form import OrderItemForm
from app.utils.decorators import check_confirmed, rate_limit
from app.services.inventory_service import InventoryService
from app.validators import validate_entity, sanitize_input, check_security
from app.security import SecurityUtils
from app.routes.api_utils import APIResponse
import logging

logger = logging.getLogger(__name__)

# Create blueprint with consistent naming
bp = Blueprint('order_items', __name__, url_prefix='/orders')


def _get_order_or_404(order_id: int):
    """Fetch an owned order or return 404."""
    return Order.query.filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first_or_404()


def _get_order_item_or_404(item_id: int, *options):
    """Fetch an owned order item by joining through the parent order."""
    query = OrderItem.query.join(Order, OrderItem.order_id == Order.id).filter(
        OrderItem.id == item_id,
        Order.user_id == current_user.id
    )
    if options:
        query = query.options(*options)
    return query.first_or_404()


@bp.route('/<int:order_id>/items/new', methods=['GET'])
@login_required
@check_confirmed
def new_order_item(order_id):
    """Render form to add a new order item."""
    order = _get_order_or_404(order_id)

    form = OrderItemForm()
    # Set product choices for the form
    form.product_id.choices = [(p.id, p.name) for p in Product.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Product.name).all()]

    # Lot choices will be populated dynamically via JavaScript
    form.lot_id.choices = []  # initially empty

    return render_template('orders/_item_form.html',
                           form=form,
                           order=order,
                           action=url_for('order_items.add_order_item', order_id=order_id))


@bp.route('/<int:order_id>/items', methods=['POST'])
@login_required
@check_confirmed
@rate_limit(max_calls=15, period=60)
def add_order_item(order_id):
    """Add an item to an order, with optional lot selection."""
    try:
        # Validate order ID
        if order_id <= 0:
            SecurityUtils.log_security_event('invalid_order_id_add_item', {
                'user_id': current_user.id,
                'order_id': order_id,
                'ip': request.remote_addr
            }, 'warning')
            return APIResponse.error(
                message="Invalid order ID",
                status_code=400,
                error_code='INVALID_ID'
            )

        order = _get_order_or_404(order_id)

        if order.status in ['completed', 'cancelled']:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': f'Cannot add items to a {order.status} order'
                }), 400
            flash(f'Cannot add items to a {order.status} order', 'warning')
            return redirect(url_for('orders.view', id=order_id))

        form = OrderItemForm()
        # Set product choices for validation
        form.product_id.choices = [(p.id, p.name) for p in Product.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Product.name).all()]

        # Lot choices are not needed for validation (will be validated separately)
        form.lot_id.choices = []

        if form.validate_on_submit():
            product = Product.query.filter_by(
                id=form.product_id.data,
                user_id=current_user.id,
                is_active=True
            ).first()
            if not product:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Product not found'}), 404
                flash('Product not found.', 'error')
                return redirect(url_for('orders.view', id=order_id))

            # Validate lot if provided
            lot_id = form.lot_id.data
            if lot_id:
                lot = InventoryLot.query.filter_by(
                    id=lot_id,
                    product_id=product.id,
                    user_id=current_user.id
                ).first()
                if not lot:
                    msg = 'Selected lot not found.'
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': msg}), 400
                    flash(msg, 'danger')
                    return redirect(url_for('orders.view', id=order_id))

                # Optional: check if lot has enough remaining quantity
                # (We'll skip this until order completion; for now just associate)
                # However, we might want to warn if lot is expired or nearly out.
                # For simplicity, we proceed.

            # Start a nested transaction
            try:
                with db.session.begin_nested():
                    order_item = OrderItem(
                        order_id=order_id,
                        product_id=product.id,
                        quantity=form.quantity.data,
                        unit_price=form.unit_price.data or product.selling_price_per_unit,
                        notes=form.notes.data,
                        lot_id=lot_id
                    )
                    db.session.add(order_item)
                    order.calculate_total()

                    # Update overall inventory if order is processing
                    if order.status == 'processing' and product.track_inventory:
                        inventory_service = InventoryService()
                        inventory_service.adjust_inventory(
                            product_id=product.id,
                            quantity=-form.quantity.data,
                            adjustment_type='sale',
                            reference_id=order.id,
                            reference_type='order',
                            notes=f'Order #{order.id} item added'
                        )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving order item: {str(e)}")
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Failed to add item.'}), 500
                flash('Failed to add item. Please try again.', 'danger')
                return redirect(url_for('orders.view', id=order_id))

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Item added successfully',
                    'redirect': url_for('orders.view', id=order_id)
                })
            flash('Item added successfully!', 'success')
            return redirect(url_for('orders.view', id=order_id))

        else:
            # Form validation failed
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Please correct the errors below',
                    'errors': form.errors
                }), 400
            # For non-AJAX, re-render the form with errors
            return render_template('orders/_item_form.html',
                                   form=form,
                                   order=order,
                                   action=url_for('order_items.add_order_item', order_id=order_id))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_order_item: {str(e)}")
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred'
            }), 500
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('orders.index'))


@bp.route('/items/<int:item_id>', methods=['GET', 'POST'])
@login_required
@check_confirmed
def edit_order_item(item_id):
    """Edit an existing order item, including lot changes."""
    order_item = _get_order_item_or_404(
        item_id,
        joinedload(OrderItem.order),
        joinedload(OrderItem.product)
    )

    if order_item.order.status in ['completed', 'cancelled']:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Cannot edit items in a {order_item.order.status} order'
            }), 400
        flash(f'Cannot edit items in a {order_item.order.status} order', 'warning')
        return redirect(url_for('orders.view', id=order_item.order_id))

    form = OrderItemForm()
    # Set product choices for validation
    form.product_id.choices = [(p.id, p.name) for p in Product.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Product.name).all()]

    # For GET, pre‑populate form
    if request.method == 'GET':
        form.id.data = order_item.id
        form.product_id.data = order_item.product_id
        form.quantity.data = order_item.quantity
        form.unit_price.data = order_item.unit_price
        form.notes.data = order_item.notes
        form.lot_id.data = order_item.lot_id  # existing lot

        # Dynamically set lot choices based on current product (via JS)
        # The template will handle it with JavaScript.

    if form.validate_on_submit():
        try:
            old_quantity = order_item.quantity
            new_quantity = form.quantity.data
            quantity_diff = new_quantity - old_quantity

            # Validate lot if changed
            new_lot_id = form.lot_id.data
            if new_lot_id != order_item.lot_id:
                # Check new lot exists and belongs to the product and user
                if new_lot_id:
                    lot = InventoryLot.query.filter_by(
                        id=new_lot_id,
                        product_id=form.product_id.data,
                        user_id=current_user.id
                    ).first()
                    if not lot:
                        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'message': 'Selected lot not found'}), 400
                        flash('Selected lot not found.', 'danger')
                        return redirect(url_for('orders.view', id=order_item.order_id))

            # Update order item
            order_item.product_id = form.product_id.data
            order_item.quantity = new_quantity
            order_item.unit_price = form.unit_price.data or order_item.product.price
            order_item.notes = form.notes.data
            order_item.lot_id = new_lot_id
            order_item.calculate_subtotal()

            # Update order total
            order = order_item.order
            order.calculate_total()

            db.session.commit()

            # Adjust inventory if quantity changed and order is processing
            if (order.status == 'processing' and
                    order_item.product and
                    order_item.product.track_inventory and
                    quantity_diff != 0):

                try:
                    inventory_service = InventoryService()
                    inventory_service.adjust_inventory(
                        product_id=order_item.product_id,
                        quantity=-quantity_diff,
                        adjustment_type='sale_update',
                        reference_id=order.id,
                        reference_type='order',
                        notes=f'Order #{order.id} item quantity updated from {old_quantity} to {new_quantity}'
                    )
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating inventory: {str(e)}")
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({
                            'success': False,
                            'message': 'Error updating inventory. Please try again.'
                        }), 500
                    flash('Error updating inventory. Please try again.', 'error')
                    return redirect(url_for('orders.view', id=order.id))

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Item updated successfully',
                    'redirect': url_for('orders.view', id=order.id)
                })

            flash('Item updated successfully!', 'success')
            return redirect(url_for('orders.view', id=order.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating order item: {str(e)}")
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'An error occurred while updating the item'
                }), 500
            flash('An error occurred while updating the item', 'error')

    # Handle validation errors for AJAX
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            return jsonify({
                'success': False,
                'message': 'Please correct the errors below',
                'errors': form.errors,
                'form': render_template('orders/_item_form.html',
                                         form=form,
                                         order=order_item.order,
                                         action=url_for('order_items.edit_order_item', item_id=item_id))
            }), 400
        else:
            # GET request should return the form HTML
            return render_template('orders/_item_form.html',
                                   form=form,
                                   order=order_item.order,
                                   action=url_for('order_items.edit_order_item', item_id=item_id))

    # For non-AJAX POST with errors, re-render the form
    return render_template('orders/_item_form.html',
                           form=form,
                           order=order_item.order,
                           action=url_for('order_items.edit_order_item', item_id=item_id))


@bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
@check_confirmed
def delete_order_item(item_id):
    """Delete an order item. No lot-specific changes needed."""
    order_item = _get_order_item_or_404(
        item_id,
        joinedload(OrderItem.order),
        joinedload(OrderItem.product)
    )

    if order_item.order.status in ['completed', 'cancelled']:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Cannot delete items from a {order_item.order.status} order'
            }), 400
        flash(f'Cannot delete items from a {order_item.order.status} order', 'warning')
        return redirect(url_for('orders.view', id=order_item.order_id))

    try:
        order = order_item.order
        product = order_item.product
        quantity = order_item.quantity

        # Delete the item
        db.session.delete(order_item)

        # Update order total
        order.calculate_total()

        db.session.commit()

        # Update inventory if order is processing and product tracks inventory
        if (order.status == 'processing' and
                product and
                product.track_inventory):

            try:
                inventory_service = InventoryService()
                inventory_service.adjust_inventory(
                    product_id=product.id,
                    quantity=quantity,
                    adjustment_type='sale_remove',
                    reference_id=order.id,
                    reference_type='order',
                    notes=f'Order #{order.id} item removed, quantity: {quantity}'
                )
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating inventory: {str(e)}")
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': 'Error updating inventory. Please try again.'
                    }), 500
                flash('Error updating inventory. Please try again.', 'error')
                return redirect(url_for('orders.view', id=order.id))

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Item removed successfully',
                'redirect': url_for('orders.view', id=order.id)
            })

        flash('Item removed successfully!', 'success')
        return redirect(url_for('orders.view', id=order.id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing order item: {str(e)}")
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An error occurred while removing the item from the order'
            }), 500
        flash('An error occurred while removing the item from the order', 'error')
        return redirect(url_for('orders.view', id=order_item.order_id))

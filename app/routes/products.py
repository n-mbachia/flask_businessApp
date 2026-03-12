# app/routes/products.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models import Product, InventoryMovement, InventoryLot
from app.forms import ProductForm, InventoryMovementForm, InventoryLotForm
from app.services.dashboard_metrics import DashboardMetrics
from app.services.inventory_service import InventoryService
from app.utils.decorators import handle_exceptions, rate_limit
from app.utils.cache import get_cache
from app.utils.helpers import save_product_image, delete_product_image
from app.validators import (
    ProductValidator, validate_entity, sanitize_input,
    check_security, SecurityValidator, validate_pagination
)
from app.security import SecurityUtils
import logging

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__)


def _generate_sku(product_name: str, user_id: int) -> str:
    """Generate a unique SKU based on product name and user ID."""
    import re
    import uuid

    clean_name = re.sub(r'[^a-zA-Z0-9]', '', product_name.upper())
    name_prefix = clean_name[:6] if clean_name else 'PROD'
    user_prefix = f"U{user_id % 1000:03d}"
    random_suffix = str(uuid.uuid4())[:8].upper()
    sku = f"{name_prefix}-{user_prefix}-{random_suffix}"

    counter = 1
    original_sku = sku
    while Product.query.filter_by(sku=sku).first():
        sku = f"{original_sku}-{counter}"
        counter += 1
        if counter > 100:
            sku = f"PROD-{user_prefix}-{uuid.uuid4().hex[:8].upper()}"
            break
    return sku

@products_bp.route('/products', methods=['GET', 'POST'])
@login_required
@handle_exceptions
@rate_limit(max_calls=20, period=60)
def manage_products():
    form = ProductForm()

    # Pagination handling
    try:
        pagination = validate_pagination(
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 10, type=int),
            max_per_page=50
        )
    except ValueError as e:
        flash(str(e), 'danger')
        pagination = {'page': 1, 'per_page': 10, 'offset': 0}

    if form.validate_on_submit():
        try:
            # Gather form data into a dictionary
            product_data = {
                'name': sanitize_input(form.name.data, 'html'),
                'description': sanitize_input(form.description.data or '', 'html'),
                'sku': sanitize_input(form.sku.data or '', 'html'),
                'barcode': sanitize_input(form.barcode.data or '', 'html'),
                'price': float(form.selling_price_per_unit.data or 0),
                'cost_price': float(form.cogs_per_unit.data or 0),
                'category': sanitize_input(form.category.data or '', 'html'),
                'reorder_point': int(form.reorder_level.data or 0),
                'initial_quantity': int(form.initial_quantity.data or 0)  # only used for creation
            }

            # Security checks
            if check_security(product_data['name'], 'all') or check_security(product_data['description'], 'all'):
                SecurityUtils.log_security_event('product_security_issue', {
                    'user_id': current_user.id,
                    'product_data': product_data,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid input detected in product data.', 'danger')
                return redirect(url_for('products.manage_products'))

            # Validate entity structure (assumes validate_entity returns (validated_data, errors))
            validated_data, errors = validate_entity('product', product_data, sanitize=False)
            if errors:
                for error in errors:
                    flash(str(error), 'danger')
                return redirect(url_for('products.manage_products'))

            product_id = request.form.get('product_id')
            product = None

            # Check for existing product with the same name (excluding current if editing)
            if product_id and product_id != 'None':
                product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
                if not product:
                    SecurityUtils.log_security_event('unauthorized_product_access', {
                        'user_id': current_user.id,
                        'product_id': product_id,
                        'ip': request.remote_addr
                    }, 'warning')
                    abort(404)

                existing = Product.query.filter(
                    Product.name == validated_data.name,
                    Product.user_id == current_user.id,
                    Product.id != product.id
                ).first()
            else:
                existing = Product.query.filter_by(name=validated_data.name, user_id=current_user.id).first()

            if existing:
                flash('Product name already exists', 'danger')
                return redirect(url_for('products.manage_products'))

            # Create or update product
            if not product:
                product = Product(user_id=current_user.id)
                SecurityUtils.log_security_event('product_created', {
                    'user_id': current_user.id,
                    'product_name': validated_data.name,
                    'ip': request.remote_addr
                }, 'info')
            else:
                SecurityUtils.log_security_event('product_updated', {
                    'user_id': current_user.id,
                    'product_id': product.id,
                    'product_name': validated_data.name,
                    'ip': request.remote_addr
                }, 'info')

            # Assign validated data
            product.name = validated_data.name
            product.description = validated_data.description
            product.sku = validated_data.sku.strip() if validated_data.sku and validated_data.sku.strip() else _generate_sku(validated_data.name, current_user.id)
            product.barcode = validated_data.barcode.strip() if validated_data.barcode else None
            product.category = validated_data.category
            product.selling_price_per_unit = validated_data.price
            product.cogs_per_unit = validated_data.cost_price
            product.reorder_level = validated_data.reorder_point

            # Calculate margin threshold (uses product's own data)
            product.margin_threshold = DashboardMetrics.calculate_margin_threshold(product)

            db.session.add(product)
            db.session.flush()  # Get product.id for image and inventory

            # Handle image upload
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                try:
                    new_image = save_product_image(image_file, product.id)
                except ValueError as image_error:
                    db.session.rollback()
                    logger.warning('Product image upload failed: %s', image_error)
                    flash(f'Product image upload failed: {image_error}', 'danger')
                    return redirect(url_for('products.manage_products'))

                if product.image_filename and product.image_filename != new_image:
                    delete_product_image(product.image_filename)
                product.image_filename = new_image

            # If creating and initial quantity > 0, create inventory movement
            if not product_id and validated_data.initial_quantity > 0:
                from app.models import InventoryMovement
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type='receipt',
                    quantity=validated_data.initial_quantity,
                    unit_cost=product.cogs_per_unit,
                    notes='Initial stock on creation'
                )
                db.session.add(movement)

            db.session.commit()
            flash('Product saved successfully!', 'success')
            return redirect(url_for('products.manage_products'))

        except Exception as e:
            logger.error(f"Error saving product: {str(e)}", exc_info=True)
            db.session.rollback()
            SecurityUtils.log_security_event('product_save_error', {
                'user_id': current_user.id,
                'error': str(e),
                'ip': request.remote_addr
            }, 'error')
            flash('An error occurred while saving the product. Please try again.', 'danger')
            return redirect(url_for('products.manage_products'))

    # Fetch paginated products for the current user
    products = Product.query.filter_by(user_id=current_user.id).paginate(
        page=pagination['page'],
        per_page=pagination['per_page']
    )

    # Convert products to JSON-serializable dicts for client-side use
    def product_to_dict(p):
        """Convert a Product ORM instance to a plain dict for JSON."""
        return {
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'barcode': p.barcode,
            'description': p.description,
            'cogs_per_unit': float(p.cogs_per_unit) if p.cogs_per_unit else 0,
            'selling_price_per_unit': float(p.selling_price_per_unit) if p.selling_price_per_unit else 0,
            'reorder_level': p.reorder_level,
            'current_stock': p.current_stock,                # assumed property
            'margin_percentage': float(p.margin_percentage) if p.margin_percentage else 0,
            'effective_margin_threshold': float(p.effective_margin_threshold) if p.effective_margin_threshold else 0,
            'category': p.category,
            'image_url': p.image_url,
        }

    products_json = [product_to_dict(p) for p in products.items]

    return render_template(
        'products/products.html',
        form=form,
        products=products,
        products_json=products_json
    )

@products_bp.route('/products/<int:product_id>/lots/new', methods=['GET', 'POST'])
@login_required
def create_lot(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    form = InventoryLotForm()

    # Populate product choices
    form.product_id.choices = [(p.id, p.name) for p in Product.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(Product.name).all()]

    if form.validate_on_submit():
        # Generate lot number if not provided
        lot_number = form.lot_number.data
        if not lot_number:
            lot_number = generate_lot_number()

        lot = InventoryLot(
            product_id=form.product_id.data,
            user_id=current_user.id,
            lot_number=lot_number,
            received_date=form.received_date.data,
            quantity_received=form.quantity_received.data,
            cost_per_unit=form.cost_per_unit.data,
            expiration_date=form.expiration_date.data
        )
        db.session.add(lot)
        db.session.commit()
        flash(f'Lot {lot.lot_number} created successfully.', 'success')
        return redirect(url_for('products.product_inventory', product_id=product_id))

    # Pre-select the current product
    form.product_id.data = product_id
    return render_template('products/lot_form.html', form=form, product=product)

@products_bp.route('/api/products/<int:product_id>/available-lots')
@login_required
def get_available_lots(product_id):
    """Return lots with remaining quantity for a product, sorted by expiration (FIFO)."""
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    lots = []
    for lot in product.lots:
        # Calculate total quantity already sold from this lot (excluding cancelled orders)
        sold = db.session.query(func.coalesce(func.sum(OrderItem.quantity), 0))\
            .join(Order)\
            .filter(OrderItem.lot_id == lot.id, Order.status != 'cancelled')\
            .scalar()
        remaining = lot.quantity_received - sold
        if remaining > 0:
            lots.append({
                'id': lot.id,
                'lot_number': lot.lot_number,
                'remaining': remaining,
                'expiration_date': lot.expiration_date.strftime('%Y-%m-%d') if lot.expiration_date else None
            })
    # FIFO sort: earliest expiration first, then by lot number
    lots.sort(key=lambda x: (x['expiration_date'] or '9999-12-31', x['lot_number']))
    return jsonify(lots)


@products_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@handle_exceptions
@rate_limit(max_calls=10, period=60)
def delete_product(product_id):
    try:
        if product_id <= 0:
            SecurityUtils.log_security_event('invalid_product_id', {
                'user_id': current_user.id,
                'product_id': product_id,
                'ip': request.remote_addr
            }, 'warning')
            abort(400)

        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            SecurityUtils.log_security_event('unauthorized_product_deletion', {
                'user_id': current_user.id,
                'product_id': product_id,
                'ip': request.remote_addr
            }, 'warning')
            abort(404)

        SecurityUtils.log_security_event('product_deleted', {
            'user_id': current_user.id,
            'product_id': product.id,
            'product_name': product.name,
            'ip': request.remote_addr
        }, 'info')

        db.session.delete(product)
        db.session.commit()
        get_cache().delete_memoized(DashboardMetrics.get_product_trends)

        flash('Product deleted successfully!', 'success')
        return redirect(url_for('products.manage_products'))

    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        SecurityUtils.log_security_event('product_deletion_error', {
            'user_id': current_user.id,
            'product_id': product_id,
            'error': str(e),
            'ip': request.remote_addr
        }, 'error')
        flash('An error occurred while deleting the product. Please try again.', 'danger')
        return redirect(url_for('products.manage_products'))


@products_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@handle_exceptions
def edit_product(product_id):
    """Return JSON with product details for editing."""
    print(f"Edit product called with ID: {product_id}, user: {current_user.id}")
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    print(f"Product found: {product}")
    if not product:
        abort(404) 

    # Return JSON for AJAX requests (modal population)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'sku': product.sku,
        'barcode': product.barcode,
        'cogs_per_unit': float(product.cogs_per_unit),
        'selling_price_per_unit': float(product.selling_price_per_unit),
        'category': product.category,
        'reorder_level': product.reorder_level
    })


@products_bp.route('/products/<int:product_id>/inventory')
@login_required
@handle_exceptions
def product_inventory(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    movements = InventoryMovement.query.filter_by(product_id=product_id)\
        .order_by(InventoryMovement.created_at.desc())\
        .all()
    return render_template(
        'products/product_inventory.html',
        product=product,
        movements=movements
    )


@products_bp.route('/products/<int:product_id>/adjust-stock', methods=['GET', 'POST'])
@login_required
@handle_exceptions
def adjust_stock(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    form = InventoryMovementForm()

    if form.validate_on_submit():
        try:
            movement_type = form.movement_type.data
            qty = int(form.quantity.data or 0)
            qty_change = qty if movement_type in ('receipt', 'adjustment_in', 'return') else -abs(qty)

            # Use the inventory service to handle the movement and update stock
            success, results = InventoryService.update_inventory_levels(
                db.session,
                current_user.id,
                updates=[{
                    'product_id': product.id,
                    'quantity_change': qty_change,
                    'adjustment_type': movement_type,
                    'unit_cost': form.unit_cost.data or product.cogs_per_unit,
                    'notes': form.notes.data
                }],
                reference_type='adjustment',
                reference_id=None,
                notes=f'Stock {movement_type} via product adjust UI'
            )

            if not success:
                error_messages = [r.get('message', 'Unknown error') for r in results if not r.get('success', True)]
                flash('Failed to update inventory: ' + '; '.join(error_messages), 'danger')
            else:
                flash('Stock updated successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating inventory: {str(e)}', 'danger')

        return redirect(url_for('products.product_inventory', product_id=product.id))

    return render_template('products/adjust_stock.html', form=form, product=product)


@products_bp.route('/products/<int:product_id>/analytics')
@login_required
def product_analytics_legacy(product_id):
    import warnings
    warnings.warn(
        'The /products/<id>/analytics route is deprecated. '
        'Use /products/<id>/analytics/dashboard instead.',
        DeprecationWarning,
        stacklevel=2
    )
    return redirect(url_for('products.product_analytics_dashboard', product_id=product_id))


@products_bp.route('/products/<int:product_id>/analytics/dashboard')
@login_required
@handle_exceptions
def product_analytics_dashboard(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    movements = InventoryMovement.query.filter_by(product_id=product_id)\
        .order_by(InventoryMovement.created_at.desc()).all()

    metrics = {
        'revenue': DashboardMetrics(current_user.id).calculate_revenue(product),
        'revenue_growth': DashboardMetrics(current_user.id).calculate_revenue_growth(product),
        'net_profit': DashboardMetrics(current_user.id).calculate_net_profit(product),
        'profit_growth': DashboardMetrics(current_user.id).calculate_profit_growth(product),
        'net_margin': DashboardMetrics(current_user.id).calculate_net_margin(product),
        'margin_growth': DashboardMetrics(current_user.id).calculate_margin_growth(product),
        'units_sold': DashboardMetrics(current_user.id).calculate_units_sold(product),
        'units_growth': DashboardMetrics(current_user.id).calculate_units_growth(product)
    }

    trend_data = DashboardMetrics(current_user.id).get_revenue_profit_trends(product_id)
    cost_data = DashboardMetrics(current_user.id).get_cost_breakdown(product_id)
    lots = DashboardMetrics(current_user.id).get_lot_analytics(product_id)
    growth_metrics = DashboardMetrics(current_user.id).get_growth_metrics(product_id)

    return render_template(
        'products/product_analytics_dashboard.html',
        product=product,
        metrics=metrics,
        trend_dates=trend_data['dates'],
        revenue_data=trend_data['revenue'],
        profit_data=trend_data['profit'],
        cost_categories=cost_data['categories'],
        cost_amounts=cost_data['amounts'],
        lots=lots,
        growth_metrics=growth_metrics,
        lot_analytics={
            'labels': [lot['lot_number'] for lot in lots],
            'sell_through_rates': [lot['sell_through_rate'] for lot in lots],
            'gross_margins': [lot['gross_margin'] for lot in lots]
        }
    )


@products_bp.route('/products/search', methods=['GET'])
@login_required
@handle_exceptions
@rate_limit(max_calls=30, period=60)
def search_products():
    try:
        query = sanitize_input(request.args.get('q', ''), 'search')
        pagination = validate_pagination(
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 10, type=int),
            max_per_page=20
        )

        if check_security(query, 'all'):
            SecurityUtils.log_security_event('product_search_security_issue', {
                'user_id': current_user.id,
                'query': query,
                'ip': request.remote_addr
            }, 'warning')
            return jsonify({'items': [], 'total': 0, 'error': 'Invalid search query'}), 400

        if not query:
            return jsonify({'items': [], 'total': 0})

        if len(query) > 100:
            return jsonify({'items': [], 'total': 0, 'error': 'Search query too long'}), 400

        search = f"%{query}%"
        products_query = Product.query.filter(
            Product.user_id == current_user.id,
            Product.is_active == True,
            (Product.name.ilike(search)) | (Product.sku.ilike(search))
        )

        products = products_query.paginate(
            page=pagination['page'],
            per_page=pagination['per_page'],
            error_out=False
        )

        items = [{
            'id': p.id,
            'text': p.name,
            'name': p.name,
            'sku': p.sku,
            'price': str(p.selling_price_per_unit) if p.selling_price_per_unit else '0.00',
            'track_inventory': p.track_inventory,
            'current_stock': p.current_stock
        } for p in products.items]

        SecurityUtils.log_security_event('product_search', {
            'user_id': current_user.id,
            'query': query,
            'results_count': len(items),
            'ip': request.remote_addr
        }, 'info')

        return jsonify({'items': items, 'total': products.total})

    except Exception as e:
        logger.error(f"Error in product search: {str(e)}", exc_info=True)
        SecurityUtils.log_security_event('product_search_error', {
            'user_id': current_user.id,
            'query': request.args.get('q', ''),
            'error': str(e),
            'ip': request.remote_addr
        }, 'error')
        return jsonify({'items': [], 'total': 0, 'error': 'Search failed'}), 500


@products_bp.route('/inventory')
@login_required
@handle_exceptions
def inventory_dashboard():
    products = Product.query.filter_by(user_id=current_user.id).all()

    total_products = len(products)
    low_stock_products = [p for p in products if p.current_stock <= p.reorder_level and p.current_stock > 0]
    out_of_stock_products = [p for p in products if p.current_stock <= 0]
    total_inventory_value = sum(p.current_stock * p.cogs_per_unit for p in products)

    recent_movements = InventoryMovement.query.join(Product)\
        .filter(Product.user_id == current_user.id)\
        .order_by(InventoryMovement.created_at.desc())\
        .limit(10)\
        .all()

    return render_template(
        'products/inventory_dashboard.html',
        products=products,
        total_products=total_products,
        low_stock_products=low_stock_products,
        out_of_stock_products=out_of_stock_products,
        total_inventory_value=total_inventory_value,
        recent_movements=recent_movements
    )

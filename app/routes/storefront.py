import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Product, InventoryMovement, User, Order, OrderItem, Customer
from app.forms.product_forms import ProductForm
from app.forms.storefront_forms import VendorInviteForm
from app.services.dashboard_metrics import DashboardMetrics
from app.services.inventory_service import InventoryService
from app.utils.decorators import handle_exceptions, rate_limit
from app.utils import csrf_exempt
from app.validators import validate_entity, sanitize_input, check_security
from app.utils.product_utils import generate_sku
from app.utils.helpers import save_product_image
from app.security import SecurityUtils
import logging

logger = logging.getLogger(__name__)

storefront_bp = Blueprint('storefront', __name__)


def _ensure_vendor():
    if not current_user.is_authenticated or not (current_user.is_vendor or current_user.is_admin):
        abort(403)


def _build_product_payload(form: ProductForm) -> dict:
    """Sanitize vendor product form data for validation."""
    payload = {
        'name': sanitize_input(form.name.data, 'html'),
        'description': sanitize_input(form.description.data or '', 'html'),
        'sku': sanitize_input(form.sku.data or '', 'html'),
        'barcode': sanitize_input(form.barcode.data or '', 'html'),
        'category': sanitize_input(form.category.data or 'Uncategorized', 'html'),
        'price': float(form.selling_price_per_unit.data or 0),
        'cost_price': float(form.cogs_per_unit.data or 0),
        'reorder_point': int(form.reorder_level.data or 0),
        'initial_quantity': int(form.initial_quantity.data or 0)
    }

    if check_security(payload['name'], 'all') or check_security(payload['description'], 'all'):
        raise ValueError('Product data failed security validation.')

    return payload


def _ensure_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@storefront_bp.route('/storefront')
@handle_exceptions
def catalog():
    """Public catalog of approved storefront products."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)

    products = Product.query.filter_by(is_active=True, is_approved=True).order_by(Product.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    flash_sale = _build_flash_sale_offer(products.items)
    return render_template('storefront/catalog.html', products=products, flash_sale=flash_sale)


def _build_flash_sale_offer(items):
    """Select one product to feature in the flash sale card."""
    candidates = [p for p in items if getattr(p, 'is_active', False) and getattr(p, 'is_approved', False) and p.selling_price_per_unit]
    if not candidates:
        return None

    candidate = max(candidates, key=lambda p: float(p.selling_price_per_unit or 0))
    base_price = float(candidate.selling_price_per_unit or 0)
    discount_percent = 15 if candidate.quantity_available >= 20 else 10
    sale_price = max(base_price * (1 - discount_percent / 100), 0.0)
    promo_code = f"FLASH{candidate.id:04d}"

    return {
        'title': candidate.name,
        'category': candidate.category,
        'vendor': candidate.user.username if candidate.user else 'Vendor',
        'original_price': f"{base_price:.2f}",
        'sale_price': f"{sale_price:.2f}",
        'discount_percent': discount_percent,
        'promo_code': promo_code
    }


@storefront_bp.route('/storefront/checkout', methods=['POST'])
@handle_exceptions
@csrf_exempt
def storefront_checkout():
    """Public endpoint that creates an order when a storefront purchase is submitted."""
    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict(flat=True)
        if 'items' in request.form:
            payload['items'] = request.form.get('items')
        if 'customer' in request.form:
            try:
                payload['customer'] = json.loads(request.form.get('customer'))
            except (ValueError, TypeError):
                payload['customer'] = {}

    items = _normalize_storefront_items(payload)
    if not items:
        return jsonify({
            'success': False,
            'message': 'Please provide at least one valid storefront item.'
        }), 400

    product_ids = {item['product_id'] for item in items}
    products = Product.query.filter(
        Product.id.in_(product_ids),
        Product.is_active == True,
        Product.is_approved == True
    ).all()

    if len(products) != len(product_ids):
        missing = product_ids - {p.id for p in products}
        return jsonify({
            'success': False,
            'message': f'Products not available: {", ".join(str(pid) for pid in missing)}'
        }), 400

    vendor_ids = {product.user_id for product in products}
    if len(vendor_ids) != 1:
        return jsonify({
            'success': False,
            'message': 'Storefront orders must contain products from a single vendor.'
        }), 400

    vendor_id = vendor_ids.pop()
    product_lookup = {product.id: product for product in products}

    subtotal = Decimal('0.00')
    order_items_data = []
    inventory_updates = []

    for entry in items:
        product = product_lookup.get(entry['product_id'])
        if not product:
            continue

        quantity_decimal = entry['quantity']
        quantity_int = int(quantity_decimal)
        if quantity_int <= 0:
            continue

        unit_price = Decimal(str(entry.get('unit_price') or product.selling_price_per_unit))
        item_subtotal = unit_price * Decimal(quantity_int)
        subtotal += item_subtotal

        order_items_data.append({
            'product': product,
            'quantity': quantity_int,
            'unit_price': unit_price,
            'notes': sanitize_input(entry.get('notes', ''), 'text')
        })
        inventory_updates.append({
            'product_id': product.id,
            'quantity_change': -float(quantity_int)
        })

    if not order_items_data:
        return jsonify({
            'success': False,
            'message': 'No valid storefront items could be processed.'
        }), 400

    validation_items = [
        {'product_id': data['product'].id, 'quantity': data['quantity']}
        for data in order_items_data
    ]
    is_valid, validation_results = InventoryService.validate_order_items(
        db.session,
        vendor_id,
        validation_items
    )
    if not is_valid:
        return jsonify({
            'success': False,
            'message': 'Inventory validation failed',
            'errors': validation_results
        }), 400

    tax_rate = _coerce_decimal(payload.get('tax_rate'), Decimal(str(current_app.config.get('SALES_TAX_RATE', 0.16))))
    if tax_rate < 0:
        tax_rate = Decimal('0.00')
    tax_amount = (subtotal * tax_rate).quantize(Decimal('0.01'))
    shipping_amount = _coerce_decimal(payload.get('shipping_amount'))
    discount_amount = _coerce_decimal(payload.get('discount_amount'))
    total_amount = subtotal + tax_amount + shipping_amount - discount_amount
    if total_amount < 0:
        total_amount = Decimal('0.00')

    requested_status = payload.get('status') or Order.STATUS_PROCESSING
    if requested_status not in dict(Order.STATUS_CHOICES):
        requested_status = Order.STATUS_PROCESSING

    payment_status = payload.get('payment_status') or Order.PAYMENT_PAID
    if payment_status not in dict(Order.PAYMENT_STATUS_CHOICES):
        payment_status = Order.PAYMENT_PAID

    payment_method = sanitize_input(payload.get('payment_method') or 'storefront', 'text')
    notes = sanitize_input(payload.get('notes', ''), 'text')
    order_date = _parse_storefront_order_date(payload.get('order_date'))

    customer = _resolve_storefront_customer(vendor_id, payload)

    try:
        with db.session.begin_nested():
            order = Order(
                user_id=vendor_id,
                customer_id=customer.id if customer else None,
                order_date=order_date,
                status=requested_status,
                payment_status=payment_status,
                payment_method=payment_method,
                notes=notes,
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_amount=shipping_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                source=Order.SOURCE_STOREFRONT
            )
            db.session.add(order)
            db.session.flush()

            for item_data in order_items_data:
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=item_data['product'].id,
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    subtotal=item_data['unit_price'] * Decimal(item_data['quantity']),
                    notes=item_data['notes']
                ))

            if inventory_updates:
                success, results = InventoryService.update_inventory_levels(
                    db.session,
                    vendor_id,
                    inventory_updates,
                    reference_type='storefront',
                    reference_id=order.id,
                    notes=f'Storefront order #{order.id}',
                    auto_commit=False
                )
                if not success:
                    error_messages = '; '.join([r.get('message', 'Unknown error') for r in results])
                    raise Exception(f'Inventory update failed: {error_messages}')

        db.session.commit()
        current_app.logger.info('Storefront order saved: %s for vendor %s', order.id, vendor_id)

        return jsonify({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'total_amount': float(order.total_amount)
        }), 201

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Storefront checkout failed: %s', exc, exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Unable to create store front order at this time.'
        }), 500


@storefront_bp.route('/storefront/vendor', methods=['GET', 'POST'])
@handle_exceptions
@rate_limit(max_calls=30, period=60)
@login_required
def vendor_portal():
    """Vendor portal for uploading products."""
    _ensure_vendor()
    form = ProductForm()
    pending_products = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()

    if form.validate_on_submit():
        try:
            payload = _build_product_payload(form)
            validated_data, errors = validate_entity('product', payload, sanitize=False)
            if errors:
                for error in errors:
                    flash(str(error), 'danger')
                return redirect(url_for('storefront.vendor_portal'))

            product = Product(
                user_id=current_user.id,
                name=validated_data.name,
                description=validated_data.description,
                category=validated_data.category,
                cogs_per_unit=validated_data.cost_price,
                selling_price_per_unit=validated_data.price,
                reorder_level=validated_data.reorder_point,
                is_active=False,
                is_approved=False
            )

            if validated_data.sku:
                if Product.query.filter_by(sku=validated_data.sku, user_id=current_user.id).first():
                    flash('SKU already exists for your account', 'danger')
                    return redirect(url_for('storefront.vendor_portal'))
                product.sku = validated_data.sku.strip()
            else:
                product.sku = generate_sku(validated_data.name, current_user.id)

            if validated_data.barcode:
                if Product.query.filter_by(barcode=validated_data.barcode, user_id=current_user.id).first():
                    flash('Barcode already exists for your account', 'danger')
                    return redirect(url_for('storefront.vendor_portal'))
                product.barcode = validated_data.barcode.strip()

            product.margin_threshold = DashboardMetrics.calculate_margin_threshold(product)
            db.session.add(product)
            db.session.flush()

            image_file = request.files.get('image')
            if image_file and image_file.filename:
                try:
                    product.image_filename = save_product_image(image_file, product.id)
                except ValueError as image_error:
                    db.session.rollback()
                    logger.warning('Vendor product image upload failed: %s', image_error)
                    flash(f'Product image upload failed: {image_error}', 'danger')
                    return redirect(url_for('storefront.vendor_portal'))

            initial_qty = validated_data.initial_quantity or 0
            if initial_qty > 0:
                movement = InventoryMovement(
                    product_id=product.id,
                    quantity=initial_qty,
                    movement_type='receipt',
                    unit_cost=product.cogs_per_unit,
                    notes='Initial stock submitted via vendor portal'
                )
                db.session.add(movement)

            db.session.commit()

            SecurityUtils.log_security_event('vendor_product_submitted', {
                'user_id': current_user.id,
                'product_id': product.id,
                'product_name': product.name
            }, 'info')

            flash('Product submitted. Awaiting admin approval before it appears in the storefront.', 'success')
            return redirect(url_for('storefront.vendor_portal'))

        except ValueError as err:
            logger.warning('Vendor product submission blocked: %s', err)
            flash(str(err), 'danger')
        except Exception as err:
            logger.error('Vendor product creation failed: %s', exc_info=True)
            db.session.rollback()
            flash('Failed to save product. Contact support if the issue persists.', 'danger')

    return render_template('storefront/vendor_portal.html', form=form, products=pending_products)


@storefront_bp.route('/storefront/admin/vendors', methods=['GET', 'POST'])
@handle_exceptions
@rate_limit(max_calls=10, period=60)
@login_required
def manage_vendors():
    """Admins can promote users to vendors."""
    _ensure_admin()
    form = VendorInviteForm()
    if form.validate_on_submit():
        email = sanitize_input(form.email.data, 'html')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account found with that email address.', 'warning')
        else:
            user.is_vendor = True
            db.session.commit()
            flash(f'{user.username} can now upload storefront products.', 'success')
    vendor_users = User.query.filter_by(is_vendor=True).order_by(User.username).all()
    return render_template('storefront/admin_vendors.html', form=form, vendors=vendor_users)


@storefront_bp.route('/storefront/admin/products/pending')
@handle_exceptions
@login_required
def pending_products():
    _ensure_admin()
    pending = Product.query.filter_by(is_approved=False).order_by(Product.created_at.desc()).all()
    return render_template('storefront/admin_pending.html', products=pending)


@storefront_bp.route('/storefront/admin/products/<int:product_id>/approve', methods=['POST'])
@handle_exceptions
@rate_limit(max_calls=20, period=60)
@login_required
def approve_product(product_id):
    _ensure_admin()
    product = Product.query.get_or_404(product_id)
    product.is_approved = True
    product.is_active = True
    db.session.commit()
    flash(f'{product.name} is now approved for the storefront.', 'success')
    return redirect(url_for('storefront.pending_products'))


@storefront_bp.route('/storefront/customer-info')
@handle_exceptions
def storefront_customer_info():
    """Return stored customer data for a vendor to prefill storefront orders."""
    vendor_id = request.args.get('vendor_id', type=int)
    if not vendor_id:
        return jsonify({'success': False, 'message': 'Vendor ID is required'}), 400

    email = sanitize_input(request.args.get('email', ''), 'text')
    phone = sanitize_input(request.args.get('phone', ''), 'text')

    if not email and not phone:
        return jsonify({'success': False, 'message': 'Enter an email or phone to look up your profile'}), 400

    query = Customer.query.filter(
        Customer.user_id == vendor_id,
        Customer.is_active == True
    )
    if email:
        query = query.filter(Customer.email.ilike(f'%{email}%'))
    if phone:
        query = query.filter(Customer.phone.ilike(f'%{phone}%'))

    customer = query.order_by(Customer.updated_at.desc()).first()
    if not customer:
        return jsonify({'success': False, 'message': 'No matching customer found'}), 404

    return jsonify({
        'success': True,
        'customer': {
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'city': customer.city,
            'state': customer.state,
            'postal_code': customer.postal_code,
            'country': customer.country,
            'hint': f'Loaded saved profile from {customer.name}'
        }
    })


def _normalize_storefront_items(payload: dict) -> list:
    """Normalize incoming storefront items into a validated list."""
    raw_items = payload.get('items')
    if raw_items is None:
        return []

    if isinstance(raw_items, str):
        try:
            raw_items = json.loads(raw_items)
        except (ValueError, TypeError):
            raw_items = []

    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    if not isinstance(raw_items, list):
        return []

    normalized = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue

        product_id = entry.get('product_id') or entry.get('id')
        quantity = entry.get('quantity', 1)
        try:
            product_id = int(product_id)
            quantity_decimal = Decimal(str(quantity))
        except (TypeError, ValueError, InvalidOperation):
            continue

        if product_id <= 0 or quantity_decimal <= 0:
            continue

        normalized.append({
            'product_id': product_id,
            'quantity': quantity_decimal,
            'notes': entry.get('notes', '')
        })

    return normalized


def _coerce_decimal(value, default=Decimal('0.00')) -> Decimal:
    """Safely convert a value to Decimal, fall back to default on error."""
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _parse_storefront_order_date(value):
    if not value:
        return datetime.utcnow()
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except (ValueError, TypeError):
        return datetime.utcnow()


def _resolve_storefront_customer(vendor_id: int, payload: dict) -> Customer | None:
    """Resolve or create a customer record for the storefront order."""
    if not vendor_id:
        return None

    customer_id = payload.get('customer_id')
    if customer_id:
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError):
            customer_id = None

    if customer_id:
        customer = Customer.query.filter_by(
            id=customer_id,
            user_id=vendor_id,
            is_active=True
        ).first()
        if customer:
            return customer

    customer_payload = payload.get('customer') or {}
    if not isinstance(customer_payload, dict):
        customer_payload = {}

    address = sanitize_input(payload.get('delivery_address') or payload.get('address') or '', 'text') or None
    city = sanitize_input(payload.get('delivery_city') or payload.get('city') or '', 'text') or None
    state = sanitize_input(payload.get('delivery_state') or payload.get('state') or '', 'text') or None
    postal_code = sanitize_input(payload.get('delivery_postal_code') or payload.get('postal_code') or '', 'text') or None
    country = sanitize_input(payload.get('delivery_country') or payload.get('country') or '', 'text') or None

    email = (customer_payload.get('email') or '').strip().lower()
    phone = (customer_payload.get('phone') or '').strip()

    if email:
        found = Customer.query.filter_by(user_id=vendor_id, email=email).first()
        if found and found.is_active:
            updated = False
            if address:
                found.address = address
                updated = True
            if city:
                found.city = city
                updated = True
            if state:
                found.state = state
                updated = True
            if postal_code:
                found.postal_code = postal_code
                updated = True
            if country:
                found.country = country
                updated = True
            if updated:
                db.session.add(found)
                db.session.flush()
            return found
    if phone:
        found = Customer.query.filter_by(user_id=vendor_id, phone=phone).first()
        if found and found.is_active:
            updated = False
            if address:
                found.address = address
                updated = True
            if city:
                found.city = city
                updated = True
            if state:
                found.state = state
                updated = True
            if postal_code:
                found.postal_code = postal_code
                updated = True
            if country:
                found.country = country
                updated = True
            if updated:
                db.session.add(found)
                db.session.flush()
            return found

    guest = Customer.query.filter_by(user_id=vendor_id, name='Storefront Guest', is_active=True).first()
    if guest:
        return guest

    name = customer_payload.get('name') or payload.get('customer_name') or 'Storefront Guest'
    company = customer_payload.get('company') or payload.get('customer_company')
    notes = customer_payload.get('notes') or payload.get('customer_notes') or 'Created via storefront checkout'

    customer = Customer(
        user_id=vendor_id,
        name=sanitize_input(name, 'text') or 'Storefront Guest',
        email=email or None,
        phone=phone or None,
        company=sanitize_input(company or '', 'text') or None,
        address=address,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
        notes=sanitize_input(notes, 'text')
    )
    db.session.add(customer)
    db.session.flush()
    return customer

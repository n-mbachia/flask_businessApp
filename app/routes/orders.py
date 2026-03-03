from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, jsonify, abort, current_app
)

from flask_login import login_required, current_user
from sqlalchemy import or_, func, text, desc
from sqlalchemy.exc import InternalError, SQLAlchemyError
from datetime import datetime, timezone
from decimal import Decimal
import json
from app.services.realtime_dashboard import RealTimeDashboard
from app.services.predictive_analytics import PredictiveAnalytics

from app import db
from app.models import Order, OrderItem, Customer, Product
from app.forms.enhanced_order_form import EnhancedOrderForm as OrderForm
from app.utils.decorators import check_confirmed, rate_limit
from app.services.inventory_service import InventoryService
from app.validators import validate_entity, sanitize_input, check_security
from app.security import SecurityUtils
from app.routes.api_utils import APIResponse
from app.utils.cache import clear_cache
from app.utils import reset_db_session, rollback_db_session
from app.services.customer_service import CustomerService

orders_bp = Blueprint('orders', __name__)


def _fetch_active_products(user_id: int):
    """Retrieve active products for the current user while handling aborted transactions."""
    def _query():
        return Product.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(Product.name).all()

    try:
        return _query()
    except InternalError as exc:
        current_app.logger.warning(
            "Product dropdown query hit an aborted transaction; reinitializing session and retrying.",
            exc_info=True
        )
        reset_db_session()
        try:
            return _query()
        except SQLAlchemyError as retry_exc:
            current_app.logger.error(
                "Product dropdown query still failing after resetting the session.",
                exc_info=True
            )
            raise retry_exc
    except SQLAlchemyError as exc:
        current_app.logger.error(
            "Unexpected database error fetching products.",
            exc_info=True
        )
        reset_db_session()
        raise exc


def _customer_context(user_id: int):
    """Build customer data payloads for the order form."""
    recent_customers = CustomerService.get_recent_customers(user_id, limit=8)
    active_customers = Customer.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(Customer.name).all()
    return recent_customers, active_customers

@orders_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@check_confirmed
@rate_limit(max_calls=10, period=60)
def complete(id):
    """Mark an order as completed and update inventory with security validation."""
    try:
        # Validate order ID
        if id <= 0:
            SecurityUtils.log_security_event('invalid_order_id_complete', {
                'user_id': current_user.id,
                'order_id': id,
                'ip': request.remote_addr
            }, 'warning')
            return APIResponse.error(
                message="Invalid order ID",
                status_code=400,
                error_code='INVALID_ID'
            )
        
        order = Order.query.get_or_404(id)
        
        # Check ownership
        if order.user_id != current_user.id:
            SecurityUtils.log_security_event('unauthorized_order_completion', {
                'user_id': current_user.id,
                'order_id': id,
                'owner_id': order.user_id,
                'ip': request.remote_addr
            }, 'warning')
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return APIResponse.error(
                    message="Unauthorized access to order",
                    status_code=403,
                    error_code='UNAUTHORIZED'
                )
            abort(403)
        
        # Don't allow completing already completed or cancelled orders
        if order.status == Order.STATUS_COMPLETED:
            msg = f'Order is already marked as {order.status}.'
            SecurityUtils.log_security_event('duplicate_order_completion', {
                'user_id': current_user.id,
                'order_id': id,
                'status': order.status,
                'ip': request.remote_addr
            }, 'warning')
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return APIResponse.error(
                    message=msg,
                    status_code=400,
                    error_code='INVALID_OPERATION'
                )
            flash(msg, 'warning')
            return redirect(url_for('orders.view', id=order.id))
        
        if order.status == Order.STATUS_CANCELLED:
            msg = 'Cannot complete a cancelled order.'
            SecurityUtils.log_security_event('invalid_order_completion_cancelled', {
                'user_id': current_user.id,
                'order_id': id,
                'ip': request.remote_addr
            }, 'warning')
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return APIResponse.error(
                    message=msg,
                    status_code=400,
                    error_code='INVALID_OPERATION'
                )
            flash(msg, 'warning')
            return redirect(url_for('orders.view', id=order.id))
        
        try:
            with db.session.begin_nested():
                # This will update inventory and mark as completed
                order.mark_as_completed(db.session)
                db.session.commit()
                
                current_app.logger.info(
                    "Order completed: id=%s user_id=%s",
                    order.id,
                    current_user.id
                )
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': 'Order marked as completed!',
                        'status': order.status,
                        'status_display': dict(Order.STATUS_CHOICES).get(order.status, order.status)
                    })
                    
                flash('Order marked as completed!', 'success')
                return redirect(url_for('orders.view', id=order.id))
                
        except Exception as e:
            db.session.rollback()
            error_msg = f'Error completing order: {str(e)}'
            current_app.logger.error(
                "Error completing order: id=%s user_id=%s error=%s",
                order.id,
                current_user.id,
                str(e)
            )
            
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 500
                
            flash(error_msg, 'danger')
            return redirect(url_for('orders.view', id=order.id))
            
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        current_app.logger.error(
            "Unexpected error completing order: id=%s user_id=%s error=%s",
            id if 'id' in locals() else 'unknown',
            current_user.id,
            str(e)
        )
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
            
        flash(error_msg, 'danger')
        return redirect(url_for('orders.index'))

@orders_bp.route('/')
@login_required
@check_confirmed
def index():
    """List all orders with filtering and pagination."""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filters
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = request.args.get('q', '')
    
    # Base query - show all non-cancelled orders by default
    orders_query = Order.query.order_by(Order.order_date.desc())
    
    # Apply status filter
    if status:
        orders_query = orders_query.filter(Order.status == status)
    else:
        # Show all statuses except 'cancelled' by default
        orders_query = orders_query.filter(Order.status != 'cancelled')
    
    if customer_id:
        orders_query = orders_query.filter(Order.customer_id == customer_id)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            orders_query = orders_query.filter(Order.order_date >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            orders_query = orders_query.filter(Order.order_date <= date_to)
        except ValueError:
            pass
    
    if query:
        search = f"%{query}%"
        orders_query = orders_query.join(Customer).filter(
            or_(
                Order.id.like(search.replace('%', '') + '%'),
                Customer.name.ilike(search),
                Customer.email.ilike(search),
                Customer.phone.ilike(search)
            )
        )
    
    # Apply relationships and pagination
    orders = orders_query.options(
        db.joinedload(Order.customer),
        db.joinedload(Order.user),
        db.joinedload(Order.items)
    ).paginate(page=page, per_page=per_page, error_out=False)
    try:
        current_app.logger.info(
            "Orders index: user_id=%s page=%s per_page=%s status=%s customer_id=%s date_from=%s date_to=%s q='%s' total=%s page_items=%s",
            current_user.id,
            page,
            per_page,
            status,
            customer_id,
            date_from,
            date_to,
            query,
            orders.total,
            len(orders.items)
        )
    except Exception:
        pass
    
    # For AJAX requests, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            current_app.logger.info(
                "Orders index AJAX: user_id=%s page=%s has_next=%s",
                current_user.id,
                page,
                orders.has_next
            )
        except Exception:
            pass
        return jsonify({
            'html': render_template('orders/_order_list.html', orders=orders),
            'has_next': orders.has_next
        })
    
    # Get customers for filter dropdown
    customers = Customer.query.filter_by(
        is_active=True
    ).order_by(Customer.name).all()

    total_customers = Customer.query.filter_by(user_id=current_user.id).count()
    active_customers = Customer.query.filter_by(user_id=current_user.id, is_active=True).count()
    guest_orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.customer_id.is_(None)
    ).count()

    completed_orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status == Order.STATUS_COMPLETED
    )
    completed_order_count = completed_orders.count()
    total_customer_revenue = completed_orders.with_entities(
        func.coalesce(func.sum(Order.total_amount), 0)
    ).scalar() or 0
    avg_order_value = total_customer_revenue / completed_order_count if completed_order_count else 0

    customers_with_orders = db.session.query(func.count(func.distinct(Order.customer_id))).filter(
        Order.user_id == current_user.id,
        Order.customer_id.isnot(None)
    ).scalar() or 0

    repeat_customers_subq = db.session.query(Order.customer_id).filter(
        Order.user_id == current_user.id,
        Order.customer_id.isnot(None)
    ).group_by(Order.customer_id).having(func.count(Order.id) > 1).subquery()
    repeat_customer_count = db.session.query(func.count()).select_from(repeat_customers_subq).scalar() or 0
    repeat_rate = (repeat_customer_count / customers_with_orders * 100) if customers_with_orders else 0
    avg_lifetime_value = total_customer_revenue / customers_with_orders if customers_with_orders else 0

    top_customers = db.session.query(
        Customer.id,
        Customer.name,
        func.count(Order.id).label('order_count'),
        func.coalesce(func.sum(Order.total_amount), 0).label('revenue'),
        func.coalesce(func.avg(Order.total_amount), 0).label('avg_order_value'),
        func.max(Order.order_date).label('last_order_date')
    ).join(Order, Order.customer_id == Customer.id).filter(
        Order.user_id == current_user.id
    ).group_by(
        Customer.id
    ).order_by(
        desc(func.sum(Order.total_amount))
    ).limit(3).all()

    customer_stats = {
        'total': total_customers,
        'active': active_customers,
        'guests': guest_orders
    }

    customer_insights = {
        'total_revenue': float(total_customer_revenue),
        'avg_order_value': float(avg_order_value),
        'repeat_rate': round(repeat_rate, 1),
        'avg_lifetime_value': float(avg_lifetime_value)
    }
    
    return render_template(
        'orders/index.html',
        orders=orders,
        customers=customers,
        status_choices=Order.STATUS_CHOICES,
        query=query,
        status=status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
        ,
        customer_stats=customer_stats,
        top_customers=top_customers
        ,
        customer_insights=customer_insights
    )

@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
@check_confirmed
def create():
    """Create a new order with inventory validation."""
    # ===== DIAGNOSTIC: Force rollback and session check =====
    print("\n=== Starting create() ===")
    try:
        db.session.rollback()
        print("Rolled back session at start.")
    except Exception as e:
        print(f"Rollback at start failed: {e}")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    tax_rate = float(current_app.config.get('SALES_TAX_RATE', 0.16))
    preselected_customer_id = request.args.get('customer_id', type=int)

    # Handle JSON data for AJAX requests
    json_data = None
    if is_ajax and request.method == 'POST':
        if request.is_json:
            json_data = request.get_json()
        else:
            json_data = request.form.to_dict()
            if request.files:
                for key, file in request.files.items():
                    json_data[key] = file

    # Initialize form with or without form data
    form = OrderForm(user_id=current_user.id, data=json_data if json_data and not request.is_json else None)
    print(f"Form initialized, items count: {len(form.items)}")
    if request.method == 'GET' and preselected_customer_id and not form.customer_id.data:
        valid_customer_ids = {choice[0] for choice in form.customer_id.choices if choice[0] > 0}
        if preselected_customer_id in valid_customer_ids:
            form.customer_id.data = preselected_customer_id

    # ===== FIX: Set product choices for all item fields with debug logging =====
    # Check session health before product query
    print("Before product query, testing session...")
    try:
        db.session.execute(text('SELECT 1'))
        print("Session is healthy.")
    except Exception as e:
        print(f"Session is BROKEN before product query: {e}")
        db.session.rollback()
        print("Session rolled back.")

    products = Product.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Product.name).all()
    print(f"Product query returned {len(products)} products.")
    product_choices = [(p.id, p.name) for p in products]
    print(f"Product choices count: {len(product_choices)}")
    if product_choices:
        print(f"First few product IDs: {[c[0] for c in product_choices[:5]]}")

    # Optional placeholder
    product_choices_with_placeholder = [(0, '-- Select Product --')] + product_choices

    # Set choices for every item field in the form
    for item in form.items:
        if hasattr(item, 'product_id'):
            item.product_id.choices = product_choices_with_placeholder
            print(f"Set choices for item: {item}")

    # If this is a POST request, ensure every submitted product is in the choices
    if request.method == 'POST':
        # Gather submitted product IDs from form data
        submitted_pids = set()
        for key in request.form:
            if key.startswith('items-') and key.endswith('-product_id'):
                try:
                    pid = int(request.form[key])
                    if pid > 0:
                        submitted_pids.add(pid)
                except ValueError:
                    pass
        print(f"Submitted product IDs: {submitted_pids}")

        # For each submitted product, ensure it's in the choices of its respective item
        for pid in submitted_pids:
            # Check if product exists and belongs to user
            extra_product = Product.query.filter_by(
                id=pid,
                user_id=current_user.id,
                is_active=True
            ).first()
            if extra_product:
                for item in form.items.entries:
                    if item.product_id.data == pid:
                        current_choices = list(item.product_id.choices)
                        # Add if not already present
                        if not any(choice[0] == pid for choice in current_choices):
                            item.product_id.choices = current_choices + [(extra_product.id, extra_product.name)]
                            print(f"Added product {pid} to item choices")
                        else:
                            print(f"Product {pid} already in choices")
            else:
                print(f"WARNING: Submitted product {pid} not found or inactive for user {current_user.id}")
    # ===== END OF FIX =====

    if form.validate_on_submit():
        # Prepare order items
        order_items = []
        if is_ajax and request.method == 'POST':
            for i in range(0, 100):
                product_key = f'items-{i}-product_id'
                quantity_key = f'items-{i}-quantity'
                unit_price_key = f'items-{i}-unit_price'

                if product_key in request.form and quantity_key in request.form:
                    product_id = request.form.get(product_key)
                    quantity = request.form.get(quantity_key)
                    unit_price = request.form.get(unit_price_key, '0.00')

                    if product_id and quantity and float(quantity) > 0:
                        order_items.append({
                            'product_id': int(product_id),
                            'quantity': float(quantity),
                            'unit_price': float(unit_price)
                        })
        else:
            for item in form.items:
                if item.product_id.data:
                    order_items.append({
                        'product_id': item.product_id.data,
                        'quantity': item.quantity.data,
                        'unit_price': item.unit_price.data or 0.0
                    })

        # Check inventory availability
        is_valid, validation_results = InventoryService.validate_order_items(
            db.session,
            current_user.id,
            order_items
        )

        if not is_valid:
            # FIX: Roll back the session – the validation query may have aborted the transaction
            db.session.rollback()

            error_messages = [
                result['message']
                for result in validation_results
                if not result['success']
            ]
            error_msg = 'Insufficient inventory for some items: ' + '; '.join(error_messages)

            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': error_msg,
                    'errors': error_messages
                }), 400

            products = _fetch_active_products(current_user.id)
            flash(error_msg, 'danger')
            return render_template('orders/form.html', form=form, tax_rate=tax_rate, products=products)

        try:
            with db.session.begin_nested():
                def _is_truthy(value):
                    if isinstance(value, bool):
                        return value
                    if value is None:
                        return False
                    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

                # Check if we should mark the order as completed.
                mark_completed = _is_truthy(request.form.get('mark_completed')) or _is_truthy(
                    json_data.get('mark_completed') if json_data else None
                )
                explicit_status = None
                if request.form.get('status') in dict(Order.STATUS_CHOICES):
                    explicit_status = request.form.get('status')
                elif json_data and str(json_data.get('status')) in dict(Order.STATUS_CHOICES):
                    explicit_status = str(json_data.get('status'))

                status = explicit_status or (Order.STATUS_COMPLETED if not is_ajax else Order.STATUS_PENDING)
                if mark_completed:
                    status = Order.STATUS_COMPLETED

                order_data = {
                    'user_id': current_user.id,
                    'order_date': datetime.now(timezone.utc),
                    'status': status,
                    'payment_status': form.payment_status.data,
                    'is_recurring': form.is_recurring.data,
                    'notes': form.notes.data,
                    'total_amount': Decimal('0.00'),
                    'subtotal': Decimal('0.00'),
                    'tax_amount': Decimal('0.00'),
                    'shipping_amount': Decimal('0.00'),
                    'discount_amount': Decimal('0.00')
                }

                if form.customer_id.data and form.customer_id.data > 0:
                    order_data['customer_id'] = form.customer_id.data
                else:
                    guest_customer = Customer.query.filter_by(
                        user_id=current_user.id,
                        name='Walk-in / Guest',
                        is_active=True
                    ).first()
                    if not guest_customer:
                        guest_customer = Customer(
                            user_id=current_user.id,
                            name='Walk-in / Guest',
                            notes='System-generated customer for guest orders.'
                        )
                        db.session.add(guest_customer)
                        db.session.flush()
                    order_data['customer_id'] = guest_customer.id

                order = Order(**order_data)
                db.session.add(order)
                db.session.flush()

                inventory_updates = []
                computed_subtotal = Decimal('0.00')
                for item_data in order_items:
                    quantity = Decimal(str(item_data['quantity']))
                    unit_price = Decimal(str(item_data.get('unit_price', 0)))
                    computed_subtotal += unit_price * quantity

                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item_data['product_id'],
                        quantity=float(quantity),
                        unit_price=unit_price,
                        subtotal=unit_price * quantity,
                        notes=item_data.get('notes', '')
                    )
                    db.session.add(order_item)

                    inventory_updates.append({
                        'product_id': item_data['product_id'],
                        'quantity_change': float(-quantity)
                    })

                tax_amount = Decimal(str(form.tax_amount.data or 0))
                shipping_amount = Decimal(str(form.shipping_amount.data or 0))
                discount_amount = Decimal(str(form.discount_amount.data or 0))
                total_amount = computed_subtotal + tax_amount + shipping_amount - discount_amount

                order.subtotal = computed_subtotal
                order.tax_amount = tax_amount
                order.shipping_amount = shipping_amount
                order.discount_amount = discount_amount
                order.total_amount = total_amount

                should_update_inventory = (
                    _is_truthy(json_data.get('update_inventory') if json_data else None) or
                    order.status == Order.STATUS_COMPLETED
                )

                if should_update_inventory and inventory_updates:
                    success, results = InventoryService.update_inventory_levels(
                        db.session,
                        current_user.id,
                        inventory_updates,
                        reference_type='order',
                        reference_id=order.id,
                        notes=f'Order #{order.id} - {order.status}',
                        auto_commit=False
                    )

                    if not success:
                        error_messages = [
                            result['message']
                            for result in results
                            if not result.get('success', True)
                        ]
                        raise Exception("Inventory update failed: " + "; ".join(error_messages))

            db.session.commit()
            order_id = order.id
            order_status = order.status

            # Real-time and predictive analytics (unchanged)
            try:
                realtime_service = current_app.extensions.get('realtime_dashboard')
                if realtime_service:
                    order_data = {
                        'id': order_id,
                        'user_id': current_user.id,
                        'total_amount': float(order.total_amount),
                        'status': order_status,
                        'customer_id': order.customer_id,
                        'created_at': order.order_date.isoformat(),
                        'customer_name': order.customer.name if order.customer else 'Guest'
                    }
                    realtime_service.broadcast_order_update(order_data)
                try:
                    anomalies = PredictiveAnalytics.detect_anomalies(
                        user_id=current_user.id,
                        metric='revenue',
                        threshold=2.0
                    )
                    if anomalies and float(order.total_amount) > 1000:
                        if realtime_service:
                            realtime_service.send_notification(current_user.id, {
                                'type': 'success',
                                'title': 'Large Order Alert',
                                'message': f'Order #{order_id} for ${order.total_amount:.2f} - unusually large!',
                                'data': {'order_id': order_id, 'amount': float(order.total_amount)},
                                'auto_dismiss': False
                            })
                    recent_orders = Order.query.filter(
                        Order.user_id == current_user.id,
                        Order.status == Order.STATUS_COMPLETED,
                        Order.order_date >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    ).count()
                    if recent_orders == 10:
                        if realtime_service:
                            realtime_service.send_notification(current_user.id, {
                                'type': 'info',
                                'title': 'Daily Sales Milestone',
                                'message': f'Congratulations! You\'ve reached {recent_orders} orders today!',
                                'data': {'orders_count': recent_orders},
                                'auto_dismiss': True
                            })
                except Exception as predictive_error:
                    current_app.logger.warning(f"Predictive analytics error during order creation: {predictive_error}")
            except Exception as realtime_error:
                current_app.logger.warning(f"Real-time update error during order creation: {realtime_error}")

            try:
                clear_cache()
            except Exception:
                pass

            if is_ajax:
                response_data = {
                    'success': True,
                    'order_id': order_id,
                    'redirect': url_for('orders.view', id=order_id)
                }
                if order_status == Order.STATUS_COMPLETED:
                    response_data.update({
                        'status': order_status,
                        'status_display': dict(Order.STATUS_CHOICES).get(order_status, order_status),
                        'message': 'Order created and marked as completed!'
                    })
                else:
                    response_data.update({
                        'status': order_status,
                        'status_display': dict(Order.STATUS_CHOICES).get(order_status, order_status),
                        'message': 'Order created successfully!'
                    })
                return jsonify(response_data)

            flash(
                'Order created and marked as completed!' if order_status == Order.STATUS_COMPLETED
                else 'Order created successfully!',
                'success'
            )
            return redirect(url_for('orders.view', id=order_id))

        except Exception as e:
            rollback_db_session()
            error_msg = f'An error occurred while creating the order: {str(e)}'
            current_app.logger.error(error_msg, exc_info=True)

            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 500

            products = _fetch_active_products(current_user.id)
            flash(error_msg, 'danger')
            recent_customers, active_customers = _customer_context(current_user.id)
            return render_template(
                'orders/form.html',
                form=form,
                title='Create Order',
                tax_rate=tax_rate,
                products=products,
                now=datetime.now(timezone.utc),
                recent_customers=recent_customers,
                customer_list_json=json.dumps([
                    {'id': customer.id, 'name': customer.name, 'company': customer.company or '', 'email': customer.email or '', 'phone': customer.phone or ''}
                    for customer in active_customers
                ])
            )

    # Handle GET requests or form validation errors
    if is_ajax:
        if request.method == 'POST':
            return jsonify({
                'success': False,
                'message': 'Form validation failed',
                'errors': form.errors
            }), 400
        return jsonify({
            'success': False,
            'message': 'GET request not supported for AJAX',
            'redirect': url_for('orders.create')
        }), 400

    if request.method == 'POST' and not form.validate_on_submit():
        current_app.logger.warning(
            "Order create validation failed: user_id=%s errors=%s",
            current_user.id,
            form.errors
        )
        # FIX: Roll back the session before re-fetching products
        db.session.rollback()
        flash('Order was not submitted. Please fix the highlighted validation errors and try again.', 'danger')

    # Get products for dropdown
    products = _fetch_active_products(current_user.id)
    recent_customers, active_customers = _customer_context(current_user.id)

    return render_template('orders/form.html',
                         form=form,
                         title='Create Order',
                         tax_rate=tax_rate,
                         products=products,
                         now=datetime.now(timezone.utc),
                         recent_customers=recent_customers,
                         customer_list_json=json.dumps([
                             {'id': customer.id, 'name': customer.name, 'company': customer.company or '', 'email': customer.email or '', 'phone': customer.phone or ''}
                             for customer in active_customers
                         ]))

@orders_bp.route('/<int:id>')
@login_required
@check_confirmed
def view(id):
    """View order details."""
    order = Order.query.options(
        db.joinedload(Order.customer),
        db.joinedload(Order.items).joinedload(OrderItem.product)
    ).get_or_404(id)
    
    # Ensure the order belongs to the current user
    if order.user_id != current_user.id:
        current_app.logger.warning(
            "Unauthorized order view attempt: user_id=%s id=%s owner_id=%s",
            current_user.id,
            id,
            order.user_id
        )
        flash(f'You do not have permission to view order {order.order_number}. This order belongs to another user.', 'danger')
        return redirect(url_for('orders.index'))
    
    try:
        current_app.logger.info(
            "Order view: user_id=%s id=%s",
            current_user.id,
            id
        )
    except Exception:
        pass
    return render_template('orders/view.html', order=order)

@orders_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@check_confirmed
def edit(id):
    """Edit an existing order."""
    try:
        current_app.logger.info(f"Edit order {id} requested by user {current_user.id}")

        order = Order.query.options(
            db.joinedload(Order.items),
            db.joinedload(Order.customer)
        ).get_or_404(id)

        current_app.logger.info(f"Order found: {order.order_number}, status: {order.status}, user_id: {order.user_id}")

        # Ensure ownership
        if order.user_id != current_user.id:
            current_app.logger.warning(f"Ownership mismatch: order.user_id={order.user_id}, current_user.id={current_user.id}")
            flash(f'You do not have permission to access order {order.order_number}. This order belongs to another user.', 'danger')
            return redirect(url_for('orders.index'))

        # Get all active products for choices
        products = Product.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Product.name).all()
        product_choices = [(p.id, p.name) for p in products]
        # Add a placeholder if you want
        product_choices.insert(0, (0, '-- Select Product --'))

        # Initialize form
        form = OrderForm(user_id=current_user.id)

        if request.method == 'GET':
            # Populate from order
            form.populate_from_order(order)
            form.status.data = order.status
            # Set choices for each item
            for item in form.items:
                if hasattr(item, 'product_id'):
                    item.product_id.choices = product_choices
        else:  # POST
            # Bind form with request data
            form = OrderForm(user_id=current_user.id, formdata=request.form)
            # Set choices for all items
            for item in form.items:
                if hasattr(item, 'product_id'):
                    item.product_id.choices = product_choices

        current_app.logger.info(f"Order {order.order_number} is editable - proceeding with form")

        # Field-level validation for completed/cancelled orders
        if order.status in ['completed', 'cancelled']:
            current_app.logger.warning(f"Order {order.order_number} is {order.status} - applying field restrictions")
            flash(f'Warning: This order is {order.status}. Only payment status, payment method, and notes can be edited.', 'warning')

        if form.validate_on_submit():
            try:
                # Apply field-level restrictions for completed/cancelled orders
                if order.status in ['completed', 'cancelled']:
                    # Only update allowed fields for completed orders
                    order.payment_status = form.payment_status.data
                    order.payment_method = form.payment_method.data
                    order.notes = form.notes.data

                    current_app.logger.info(f"Updated {order.status} order {order.order_number} - restricted fields only")
                    flash(f'{order.status.title()} order updated successfully. Only payment information and notes were modified.', 'success')
                else:
                    # Full update for active orders
                    order.customer_id = form.customer_id.data if form.customer_id.data else None
                    order.order_date = form.order_date.data
                    if form.status.data in dict(Order.STATUS_CHOICES):
                        order.status = form.status.data
                    order.payment_status = form.payment_status.data
                    order.payment_method = form.payment_method.data
                    order.notes = form.notes.data

                    # Recalculate totals if needed
                    if hasattr(order, 'calculate_total'):
                        order.calculate_total()

                    current_app.logger.info(f"Updated active order {order.order_number} - all fields")
                    flash('Order updated successfully!', 'success')

                db.session.commit()
                return redirect(url_for('orders.view', id=order.id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating order {id}: {str(e)}")
                flash('An error occurred while updating the order.', 'error')
        elif request.method == 'POST':
            # Form was submitted but validation failed
            flash('Please correct the errors below.', 'error')
            # (The duplicate elif was removed)

        # Get products for template (for JavaScript "Add Item")
        products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()

        current_app.logger.info(f"Rendering edit form for order {order.order_number}")

        return render_template(
            'orders/form.html',
            form=form,
            order=order,
            title='Edit Order',
            products=products,
            tax_rate=float(current_app.config.get('SALES_TAX_RATE', 0.16)),
            now=datetime.now(timezone.utc)
        )

    except Exception as e:
        current_app.logger.error(f"Unexpected error in edit route: {str(e)}", exc_info=True)
        raise

@orders_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@check_confirmed
def cancel(id):
    """Cancel an order and return items to inventory."""
    order = Order.query.get_or_404(id)
    
    # Check if the order belongs to the current user
    if order.user_id != current_user.id:
        try:
            current_app.logger.warning(
                "Unauthorized order cancel attempt: user_id=%s id=%s owner_id=%s",
                current_user.id,
                id,
                order.user_id
            )
        except Exception:
            pass
        abort(403)
    
    # Don't allow cancelling already completed or cancelled orders
    if order.status in [Order.STATUS_COMPLETED, Order.STATUS_CANCELLED]:
        try:
            current_app.logger.info(
                "Order cancel not allowed: user_id=%s id=%s status=%s",
                current_user.id,
                id,
                order.status
            )
        except Exception:
            pass
        flash(f'Cannot cancel an order that is already {order.status}.', 'warning')
        return redirect(url_for('orders.view', id=order.id))
    
    try:
        with db.session.begin_nested():
            # If order was completed, return items to inventory
            if order.status == Order.STATUS_COMPLETED:
                from app.services.inventory_service import InventoryService
                
                # Prepare inventory updates to return items
                inventory_updates = []
                for item in order.items:
                    inventory_updates.append({
                        'product_id': item.product_id,
                        'quantity_change': float(item.quantity)  # Positive to return to inventory
                    })
                
                # Update inventory
                try:
                    current_app.logger.info(
                        "Order cancel inventory return: user_id=%s id=%s items=%d",
                        current_user.id,
                        id,
                        len(order.items)
                    )
                except Exception:
                    pass
                success, results = InventoryService.update_inventory_levels(
                    db.session,
                    current_user.id,
                    inventory_updates,
                    reference_type='order_cancel',
                    reference_id=order.id,
                    notes=f'Order #{order.id} cancelled - items returned to inventory'
                )
                
                if not success:
                    error_messages = [
                        result['message'] 
                        for result in results 
                        if not result.get('success', True)
                    ]
                    raise Exception("Inventory update failed: " + "; ".join(error_messages))
            
            # Update order status
            order.status = Order.STATUS_CANCELLED
            order.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            try:
                current_app.logger.info(
                    "Order cancelled: id=%s user_id=%s",
                    order.id,
                    current_user.id
                )
            except Exception:
                pass
            flash('Order has been cancelled and items returned to inventory.', 'success')
            return redirect(url_for('orders.view', id=order.id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order {id}: {str(e)}", exc_info=True)
        flash(f'An error occurred while cancelling the order: {str(e)}', 'danger')
        return redirect(url_for('orders.view', id=order.id))

@orders_bp.route('/api/calculate-totals', methods=['POST'])
@login_required
def calculate_totals():
    """Calculate order totals (AJAX endpoint)."""
    try:
        data = request.get_json()
        
        # Calculate subtotal from items
        subtotal = 0
        for item in data.get('items', []):
            if item.get('product_id') and item.get('quantity') and item.get('unit_price'):
                quantity = Decimal(str(item['quantity']))
                unit_price = Decimal(str(item['unit_price']))
                subtotal += quantity * unit_price
        
        # Calculate tax
        tax_rate = Decimal(str(data.get('tax_rate', 0))) # /100
        tax_amount = subtotal * tax_rate
        
        # Get other amounts
        shipping = Decimal(str(data.get('shipping_amount', 0)))
        discount = Decimal(str(data.get('discount_amount', 0)))
        
        # Calculate total
        total = (subtotal + tax_amount + shipping) - discount
        
        return jsonify({
            'success': True,
            'subtotal': f"{subtotal:.2f}",
            'tax_amount': f"{tax_amount:.2f}",
            'shipping': f"{shipping:.2f}",
            'discount': f"{discount:.2f}",
            'total': f"{total:.2f}"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error calculating totals: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while calculating totals'
        }), 500

@orders_bp.route('/api/product/<int:product_id>')
@login_required
def get_product(product_id):
    """Get product details (AJAX endpoint)."""
    product = Product.query.filter_by(
        id=product_id,
        user_id=current_user.id,
        is_active=True
    ).first_or_404()
    
    try:
        current_app.logger.info(
            "Product fetched for order: user_id=%s product_id=%s",
            current_user.id,
            product_id
        )
    except Exception:
        pass
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': float(product.selling_price_per_unit) if product.selling_price_per_unit else 0.0,
        'sku': product.sku,
        'stock': product.current_stock
    })

@orders_bp.route('/api/products/search')
@login_required
def search_products():
    """Search for products by name or SKU."""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    search = f"%{query}%"
    
    # Query products that match the search term and are active
    products = Product.query.filter(
        Product.user_id == current_user.id,
        Product.is_active == True,
        or_(
            Product.name.ilike(search),
            Product.sku.ilike(search),
            Product.barcode.ilike(search)
        )
    ).limit(20).all()
    
    # Format the response
    result = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'barcode': p.barcode,
        'price': float(p.selling_price_per_unit) if p.selling_price_per_unit else 0.0,
        'stock': p.current_stock,
        'category': p.category
    } for p in products]
    
    try:
        current_app.logger.info(
            "Product search: user_id=%s q='%s' results=%d",
            current_user.id,
            query,
            len(result)
        )
    except Exception:
        pass
    return jsonify(result)

@orders_bp.route('/api/customers/search')
@login_required
def search_customers():
    """Search for customers by name, email, or phone."""
    from app.models import Customer
    
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    search = f"%{query}%"
    
    # Query customers that match the search term and belong to the current user
    customers = Customer.query.filter(
        Customer.user_id == current_user.id,
        Customer.is_active == True,
        or_(
            Customer.name.ilike(search),
            Customer.email.ilike(search),
            Customer.phone.ilike(search)
        )
    ).order_by(Customer.name).limit(10).all()
    
    # Format the response
    result = [{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'phone': c.phone,
        'company': c.company
    } for c in customers]
    
    try:
        current_app.logger.info(
            "Customer search: user_id=%s q='%s' results=%d",
            current_user.id,
            query,
            len(result)
        )
    except Exception:
        pass
    return jsonify(result)

@orders_bp.route('/export')
@login_required
@check_confirmed
def export():
    """Export orders to CSV."""
    import csv
    from io import StringIO
    from flask import Response
    
    # Get filter parameters
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = Order.query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Order.order_date >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Order.order_date <= date_to)
        except ValueError:
            pass
    
    # Get orders with related data
    orders = query.options(
        db.joinedload(Order.customer),
        db.joinedload(Order.items).joinedload(OrderItem.product)
    ).order_by(Order.order_date.desc()).all()
    try:
        current_app.logger.info(
            "Orders export: user_id=%s status=%s customer_id=%s date_from=%s date_to=%s count=%d",
            current_user.id,
            status,
            customer_id,
            date_from,
            date_to,
            len(orders)
        )
    except Exception:
        pass
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Order ID', 'Order Date', 'Customer', 'Status', 'Payment Status',
        'Subtotal', 'Tax', 'Shipping', 'Discount', 'Total', 'Items'
    ])
    
    # Write data
    for order in orders:
        items = ', '.join([
            f"{item.quantity}x {item.product.name} (${item.unit_price} each)" 
            for item in order.items
        ])
        
        writer.writerow([
            order.id,
            order.order_date.strftime('%Y-%m-%d %H:%M'),
            order.customer.name if order.customer else '',
            order.status.capitalize(),
            order.payment_status.capitalize().replace('_', ' '),
            f"${order.subtotal:.2f}",
            f"${order.tax_amount:.2f}",
            f"${order.shipping_amount:.2f}",
            f"${order.discount_amount:.2f}",
            f"${order.total_amount:.2f}",
            items
        ])
    
    # Create response with CSV file
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=orders_export.csv',
            'Content-type': 'text/csv; charset=utf-8'
        }
    )

@orders_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@check_confirmed
def delete_order(id):
    """Delete an order (cascades to items)."""
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        abort(403)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted successfully.', 'success')
    return redirect(url_for('orders.index'))

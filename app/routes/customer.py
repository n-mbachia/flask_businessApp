from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)

from flask_login import login_required, current_user
from sqlalchemy import or_, func, and_
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
from app import db
from app.models.customer import Customer
from app.models.orders import Order
from app.forms.customer_form import CustomerForm
from app.utils.decorators import check_confirmed, rate_limit
from app.utils import is_safe_url, reset_db_session
from app.validators import validate_entity, sanitize_input, check_security, validate_pagination
from app.security import SecurityUtils
from app.routes.api_utils import APIResponse

# Import new service layer
try:
    from app.services.customer_service import CustomerService
    from app.utils.exceptions import ValidationError, BusinessLogicError, NotFoundError
    _HAS_CUSTOMER_SERVICE = True
except ImportError:
    _HAS_CUSTOMER_SERVICE = False

customer_bp = Blueprint('customer', __name__)


def _customers_for_current_user():
    """Return a customer query scoped to the authenticated user."""
    return Customer.query.filter(Customer.user_id == current_user.id)


def _get_customer_or_404(customer_id: int):
    """Fetch an owned customer or return 404."""
    return _customers_for_current_user().filter(Customer.id == customer_id).first_or_404()


class SafePagination:
    """Minimal pagination stand-in for error fallbacks."""

    def __init__(self, items=None, page=1, per_page=20, total=None):
        self.items = items or []
        self.page = max(1, page or 1)
        self.per_page = max(1, per_page or 1)
        self.total = self._resolve_total(total)
        self.pages = self._calculate_pages()

    def _resolve_total(self, total):
        if total is None:
            return len(self.items)
        return max(0, total)

    def _calculate_pages(self):
        if self.total <= 0:
            return 1
        return max(1, (self.total + self.per_page - 1) // self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return max(1, self.page - 1)

    @property
    def next_num(self):
        return min(self.pages, self.page + 1)

    def iter_pages(self, **_):
        if self.pages <= 1:
            return []
        return list(range(1, self.pages + 1))

@customer_bp.route('/')
@login_required
@check_confirmed
@rate_limit(max_calls=30, period=60)
def index():
    """List all customers with pagination and search with security validation."""
    try:
        # Validate and sanitize input parameters
        pagination = validate_pagination(
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 20, type=int),
            max_per_page=50
        )
        
        query = sanitize_input(request.args.get('q', ''), 'search')
        
        # Check for security issues in search query
        if check_security(query, 'all'):
            SecurityUtils.log_security_event('customer_search_security_issue', {
                'user_id': current_user.id,
                'query': query,
                'ip': request.remote_addr
            }, 'warning')
            flash('Invalid search query detected.', 'danger')
            return redirect(url_for('customer.index'))
        
        # Limit query length
        if len(query) > 100:
            SecurityUtils.log_security_event('customer_search_too_long', {
                'user_id': current_user.id,
                'query_length': len(query),
                'ip': request.remote_addr
            }, 'warning')
            flash('Search query is too long.', 'danger')
            return redirect(url_for('customer.index'))
        
        # Base query
        customers_query = Customer.query.filter_by(user_id=current_user.id)
        
        # Apply search filter if query exists
        if query:
            search = f"%{query}%"
            customers_query = customers_query.filter(
                or_(
                    Customer.name.ilike(search),
                    Customer.email.ilike(search),
                    Customer.phone.ilike(search),
                    Customer.company.ilike(search)
                )
            )
        
        # Order and paginate
        customers = customers_query.order_by(
            Customer.name.asc()
        ).paginate(
            page=pagination['page'], 
            per_page=pagination['per_page'],
            error_out=False
        )
        
        SecurityUtils.log_security_event('customer_list_access', {
            'user_id': current_user.id,
            'query': query,
            'page': pagination['page'],
            'results_count': len(customers.items),
            'ip': request.remote_addr
        }, 'info')
        
        return render_template(
            'customer/index.html',
            customers=customers,
            query=query
        )
        
    except Exception as e:
        reset_db_session()
        current_app.logger.error(f"Error listing customers: {str(e)}", exc_info=True)
        SecurityUtils.log_security_event('customer_list_error', {
            'user_id': current_user.id,
            'error': str(e),
            'ip': request.remote_addr
        }, 'error')
        flash('An error occurred while loading customers. Please try again.', 'danger')
        pagination_data = locals().get('pagination', {'page': 1, 'per_page': 20})
        safe_customers = SafePagination(
            items=[],
            page=pagination_data.get('page', 1),
            per_page=pagination_data.get('per_page', 20)
        )
        return render_template('customer/index.html', customers=safe_customers, query='')
    
    # For AJAX requests, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'html': render_template('customers/_customer_list.html', customers=customers),
            'has_next': customers.has_next
        })
    
    return render_template('customers/index.html', customers=customers, query=query)

@customer_bp.route('/create', methods=['GET', 'POST'])
@login_required
@check_confirmed
def create():
    """Create a new customer."""
    form = CustomerForm()
    next_page = request.args.get('next') or request.form.get('next')
    
    if form.validate_on_submit():
        try:
            # Prepare customer data
            customer_data = {
                'name': form.name.data,
                'email': form.email.data,
                'phone': form.phone.data,
                'company': form.company.data,
                'address': form.address.data,
                'city': form.city.data,
                'state': form.state.data,
                'postal_code': form.postal_code.data,
                'country': form.country.data,
                'tax_id': form.tax_id.data,
                'notes': form.notes.data,
                'is_active': True
            }
            
            if _HAS_CUSTOMER_SERVICE:
                # Service layer handles creation and commit
                customer = CustomerService.create_customer(current_user.id, customer_data)
            else:
                # Fallback: direct ORM
                customer = Customer(**customer_data)
                customer.user_id = current_user.id
                db.session.add(customer)
                db.session.commit()
            
            # ---- SUCCESS HANDLING ----
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'id': customer.id,
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'company': customer.company
                }), 201
            
            flash('Customer created successfully!', 'success')
            
            # Safe redirect
            if next_page and is_safe_url(next_page):
                # Preselect customer for order creation if applicable
                parsed = urlparse(next_page)
                if parsed.path == url_for('orders.create'):
                    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                    query_params['customer_id'] = str(customer.id)
                    parsed = parsed._replace(query=urlencode(query_params))
                    next_page = urlunparse(parsed)
                return redirect(next_page)
            
            return redirect(url_for('customer.view', id=customer.id))
            
        except (ValidationError, BusinessLogicError, NotFoundError) as e:
            reset_db_session()
            current_app.logger.error(f"Service error creating customer: {e}", exc_info=True)
            error_message = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_message, 'error_type': type(e).__name__}), 400
            flash(error_message, 'danger')
            
        except Exception as e:
            reset_db_session()
            current_app.logger.error(f"Unexpected error creating customer: {e}", exc_info=True)
            error_message = f'Error creating customer: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_message}), 400
            flash(error_message, 'danger')
    
    # Handle AJAX validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Validation Error', 'errors': form.errors}), 400
    
    return render_template('customer/form.html', 
                         form=form, 
                         title='Create Customer',
                         next=next_page)

@customer_bp.route('/<int:id>')
@login_required
@check_confirmed
def view(id):
    """View a customer's details."""
    customer = _get_customer_or_404(id)
    
    return render_template('customers/view.html', customer=customer)

@customer_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@check_confirmed
def edit(id):
    """Edit an existing customer."""
    customer = _get_customer_or_404(id)
    
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(customer)
            db.session.commit()
            
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customer.view', id=customer.id))
        except Exception as e:
            reset_db_session()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    return render_template(
        'customer/form.html', 
        form=form, 
        customer=customer,
        title=f'Edit {customer.name}'
    )

@customer_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@check_confirmed
def delete(id):
    """Delete a customer."""
    customer = _get_customer_or_404(id)
    
    try:
        # Check if customer has orders
        if customer.orders:
            flash('Cannot delete customer with existing orders. Please delete the orders first.', 'danger')
        else:
            db.session.delete(customer)
            db.session.commit()
            flash('Customer deleted successfully!', 'success')
    except Exception as e:
        reset_db_session()
        flash(f'Error deleting customer: {str(e)}', 'danger')
    
    return redirect(url_for('customer.index'))

@customer_bp.route('/search')
@login_required
@check_confirmed
def search():
    """Search for customers (AJAX endpoint) with enhanced search capabilities."""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)  # Cap at 50 results
        fields = request.args.get('fields', 'name,email,phone,company').split(',')
        exact = request.args.get('exact', 'false').lower() == 'true'
        
        if not query:
            return jsonify([])
        
        # Build search conditions
        conditions = []
        search_term = query if exact else f'%{query}%'
        
        # Field mappings for search
        field_mappings = {
            'name': Customer.name,
            'email': Customer.email,
            'phone': Customer.phone,
            'company': Customer.company,
            'address': Customer.address
        }
        
        # Add conditions for each requested field
        for field in fields:
            field = field.strip()
            if field in field_mappings:
                if exact:
                    conditions.append(field_mappings[field] == search_term)
                else:
                    conditions.append(field_mappings[field].ilike(search_term))
        
        if not conditions:
            return jsonify([])
        
        # Combine conditions with OR and filter by user
        query_condition = or_(*conditions)
        query_condition = and_(query_condition, Customer.user_id == current_user.id)
        
        # Execute query with similarity-based ordering
        customers = Customer.query.filter(query_condition)\
                                .order_by(
                                    db.func.similarity(Customer.name, query).desc(),
                                    Customer.name
                                )\
                                .limit(limit)\
                                .all()
        
        # Format results
        results = [{
            'id': c.id,
            'name': c.name,
            'email': c.email or '',
            'phone': c.phone or '',
            'company': c.company or '',
            'address': c.address or '',
            'is_active': c.is_active,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'total_orders': len(c.orders) if hasattr(c, 'orders') else 0,
            'last_order_date': max([o.order_date for o in c.orders], default=None) 
                            if hasattr(c, 'orders') and c.orders else None
        } for c in customers]
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f'Error in customer search: {str(e)}', exc_info=True)
        return jsonify({'error': 'An error occurred while searching for customers'}), 500

@customer_bp.route('/api/search', methods=['GET'])
@login_required
def search_api():
    """Enhanced customer search API with pagination and advanced filtering."""
    try:
        # Parse query parameters
        query = request.args.get('q', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
        sort_field = request.args.get('sort', 'name')
        sort_order = request.args.get('order', 'asc')
        status_filter = request.args.get('status', 'active')
        has_orders = request.args.get('has_orders')
        
        # Start building the query
        customers_query = Customer.query.filter_by(user_id=current_user.id)
        
        # Apply search filter
        if query:
            search = f'%{query}%'
            customers_query = customers_query.filter(
                or_(
                    Customer.name.ilike(search),
                    Customer.email.ilike(search),
                    Customer.phone.ilike(search),
                    Customer.company.ilike(search),
                    Customer.address.ilike(search)
                )
            )
        
        # Apply status filter
        if status_filter == 'active':
            customers_query = customers_query.filter(Customer.is_active == True)
        elif status_filter == 'inactive':
            customers_query = customers_query.filter(Customer.is_active == False)
        
        # Apply order filter
        if has_orders is not None:
            has_orders = has_orders.lower() == 'true'
            if has_orders:
                customers_query = customers_query.filter(Customer.orders.any())
            else:
                customers_query = customers_query.filter(~Customer.orders.any())
        
        # Apply sorting
        sort_column = getattr(Customer, sort_field, Customer.name)
        if sort_order.lower() == 'desc':
            sort_column = sort_column.desc()
        customers_query = customers_query.order_by(sort_column)
        
        # Execute paginated query
        pagination = customers_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format results
        customers = []
        for customer in pagination.items:
            customers.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'company': customer.company or '',
                'address': customer.address or '',
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
                'total_orders': len(customer.orders) if hasattr(customer, 'orders') else 0,
                'last_order_date': max([o.order_date for o in customer.orders], default=None) 
                                if hasattr(customer, 'orders') and customer.orders else None
            })
        
        # Return paginated results
        return jsonify({
            'items': customers,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in customer API search: {str(e)}', exc_info=True)
        return jsonify({'error': 'An error occurred while processing your request'}), 500

@customer_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
@check_confirmed
def toggle_status(id):
    """Toggle customer active status (AJAX endpoint)."""
    customer = _get_customer_or_404(id)
    
    try:
        customer.is_active = not customer.is_active
        db.session.commit()
        return jsonify({
            'success': True, 
            'is_active': customer.is_active,
            'message': f"Customer {'activated' if customer.is_active else 'deactivated'} successfully"
        })
    except Exception as e:
        reset_db_session()
        return jsonify({'success': False, 'message': str(e)}), 500

@customer_bp.route('/<int:id>/details')
@login_required
def customer_details(id):
    """Get customer details in JSON format."""
    customer = _get_customer_or_404(id)
    
    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'email': customer.email or '',
        'phone': customer.phone or '',
        'address': customer.address or '',
        'city': customer.city or '',
        'state': customer.state or '',
        'postal_code': customer.postal_code or '',
        'company': customer.company or ''
    })

@customer_bp.route('/export')
@login_required
@check_confirmed
def export():
    """Export customers to CSV or Excel."""
    import io
    import csv
    from flask import Response
    
    # Get all customers for the current user
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Name', 'Email', 'Phone', 'Company', 'Address', 'City', 
        'State', 'Postal Code', 'Country', 'Tax ID', 'Status'
    ])
    
    # Write data
    for customer in customers:
        writer.writerow([
            customer.name,
            customer.email or '',
            customer.phone or '',
            customer.company or '',
            customer.address or '',
            customer.city or '',
            customer.state or '',
            customer.postal_code or '',
            customer.country or '',
            customer.tax_id or '',
            'Active' if customer.is_active else 'Inactive'
        ])
    
    # Create response with CSV file
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=customers_export.csv',
            'Content-type': 'text/csv; charset=utf-8'
        }
    )

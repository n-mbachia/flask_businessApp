# app/routes/sales.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import logging
from app import db
from app.models import Sales, Product
from app.forms import SalesForm
from app.utils.decorators import rate_limit
from app.validators import validate_entity, sanitize_input, check_security
from app.security import SecurityUtils
from app.routes.api_utils import APIResponse

logger = logging.getLogger(__name__)
sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/', methods=['GET', 'POST'])
@login_required
@rate_limit(max_calls=20, period=60)
def manage_sales():
    """View and create sales records with security validation."""
    form = SalesForm(user_id=current_user.id)

    if form.validate_on_submit():
        try:
            # Validate and sanitize input data
            customer_name = sanitize_input(form.customer_name.data or '', 'html')
            notes = sanitize_input(form.notes.data or '', 'html')
            
            # Check for security issues
            if check_security(customer_name, 'all') or check_security(notes, 'all'):
                SecurityUtils.log_security_event('sales_security_issue', {
                    'user_id': current_user.id,
                    'customer_name': customer_name,
                    'notes': notes,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid input detected in sales data.', 'danger')
                return redirect(url_for('sales.manage_sales'))
            
            # Validate units sold
            if form.units_sold.data < 0 or form.units_sold.data > 100000:
                SecurityUtils.log_security_event('invalid_units_sold', {
                    'user_id': current_user.id,
                    'units_sold': form.units_sold.data,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid units sold value.', 'danger')
                return redirect(url_for('sales.manage_sales'))
            
            # Get the product to ensure it belongs to the user
            product = Product.query.filter_by(
                id=form.product_id.data, 
                user_id=current_user.id
            ).first()
            
            if not product:
                SecurityUtils.log_security_event('unauthorized_product_sale', {
                    'user_id': current_user.id,
                    'product_id': form.product_id.data,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid product selected.', 'danger')
                return redirect(url_for('sales.manage_sales'))

            # Create a new sale record using the correct field names
            sale = Sales(
                product_id=product.id,
                month=form.date.data.strftime('%Y-%m'),  # Format as YYYY-MM
                units_sold=form.units_sold.data,
                customer_name=customer_name,
                notes=notes,
                user_id=current_user.id
            )

            db.session.add(sale)
            db.session.commit()
            
            SecurityUtils.log_security_event('sale_recorded', {
                'user_id': current_user.id,
                'sale_id': sale.id,
                'product_id': product.id,
                'units_sold': form.units_sold.data,
                'ip': request.remote_addr
            }, 'info')

            flash('Sale recorded successfully!', 'success')
            
            # If the request is AJAX, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return APIResponse.success(
                    data={'sale_id': sale.id},
                    message='Sale recorded successfully!'
                )
                
            return redirect(url_for('sales.manage_sales'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving sale: {e}", exc_info=True)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'error',
                    'message': 'An error occurred while saving the sale.'
                }), 400
                
            flash('An error occurred while saving the sale.', 'danger')
    
    # Handle GET request or form validation errors
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get sales records for the current user with product details
    sales_query = db.session.query(
        Sales,
        Product.name.label('product_name'),
        (Sales.units_sold * Product.selling_price_per_unit).label('total_amount')
    ).join(
        Product, Product.id == Sales.product_id
    ).filter(
        Product.user_id == current_user.id
    ).order_by(
        desc(Sales.month)
    )
    
    # Apply search filter if provided
    search = request.args.get('search')
    if search:
        sales_query = sales_query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Sales.customer_name.ilike(f'%{search}%')) |
            (Sales.notes.ilike(f'%{search}%'))
        )
    
    # Apply date range filter if provided
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            sales_query = sales_query.filter(Sales.month >= start_date.strftime('%Y-%m'))
        except ValueError:
            pass
            
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            # Convert end_date to the last day of the month for inclusive filtering
            next_month = end_date.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            sales_query = sales_query.filter(Sales.month <= last_day.strftime('%Y-%m'))
        except ValueError:
            pass
    
    # Paginate the results
    pagination = sales_query.paginate(page=page, per_page=per_page, error_out=False)
    sales = pagination.items
    
    # Calculate summary data
    summary = {
        'total_sales': sum(sale.units_sold for sale, _, _ in sales) if sales else 0,
        'total_revenue': sum(float(amount) for _, _, amount in sales if amount) if sales else 0,
        'total_products': len(set(sale.product_id for sale, _, _ in sales)) if sales else 0
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'sales': [{
                'id': sale.id,
                'date': sale.month,
                'product_name': product_name,
                'customer_name': sale.customer_name,
                'quantity': sale.units_sold,
                'unit_price': sale.units_sold and float(total_amount) / sale.units_sold if sale.units_sold > 0 else 0,
                'total_amount': float(total_amount) if total_amount else 0,
                'notes': sale.notes
            } for sale, product_name, total_amount in sales],
            'summary': summary,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total
        })
    
    return render_template(
        'sales/sales.html',
        form=form,
        sales=sales,
        pagination=pagination,
        summary=summary,
        search=search or '',
        start_date=start_date.strftime('%Y-%m-%d') if start_date else '',
        end_date=end_date.strftime('%Y-%m-%d') if end_date else ''
    )

@sales_bp.route('/edit/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def edit_sale(sale_id):
    """Edit an existing sale record."""
    sale = Sales.query.get_or_404(sale_id)
    
    # Verify the sale belongs to the current user
    if sale.product.user_id != current_user.id:
        abort(403)
    
    form = SalesForm(obj=sale, user_id=current_user.id)
    
    if form.validate_on_submit():
        try:
            # Update the sale record with form data
            sale.month = form.date.data.strftime('%Y-%m')
            sale.units_sold = form.units_sold.data
            sale.customer_name = form.customer_name.data or None
            sale.notes = form.notes.data or None
            
            db.session.commit()
            
            flash('Sale updated successfully!', 'success')
            return redirect(url_for('sales.sales'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating sale {sale_id}: {e}", exc_info=True)
            flash('An error occurred while updating the sale.', 'danger')
    
    # Pre-fill the form with the sale data
    if request.method == 'GET':
        form.date.data = datetime.strptime(sale.month + '-01', '%Y-%m-%d').date()
        form.units_sold.data = sale.units_sold
        form.customer_name.data = sale.customer_name
        form.notes.data = sale.notes
    
    return render_template('sales/edit_sale.html', form=form, sale=sale)

@sales_bp.route('/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    """Delete a sale record."""
    sale = Sales.query.get_or_404(sale_id)
    
    # Verify the sale belongs to the current user
    if sale.product.user_id != current_user.id:
        abort(403)
    
    try:
        db.session.delete(sale)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'message': 'Sale deleted successfully!'
            })
            
        flash('Sale deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting sale {sale_id}: {e}", exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'error',
                'message': 'An error occurred while deleting the sale.'
            }), 400
            
        flash('An error occurred while deleting the sale.', 'danger')
    
    return redirect(url_for('sales.sales'))

@sales_bp.route('/api/summary')
@login_required
def sales_summary():
    """Get sales summary data for charts and dashboards."""
    # Get sales data for the last 12 months
    twelve_months_ago = (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m')
    
    # Query sales data grouped by month
    monthly_sales = db.session.query(
        Sales.month,
        func.sum(Sales.units_sold).label('total_units'),
        func.sum(Sales.units_sold * Product.selling_price_per_unit).label('total_revenue')
    ).join(
        Product, Product.id == Sales.product_id
    ).filter(
        Product.user_id == current_user.id,
        Sales.month >= twelve_months_ago
    ).group_by(
        Sales.month
    ).order_by(
        Sales.month
    ).all()
    
    # Format data for charts
    months = []
    units = []
    revenue = []
    
    for month_data in monthly_sales:
        months.append(month_data.month)
        units.append(month_data.total_units or 0)
        revenue.append(float(month_data.total_revenue) if month_data.total_revenue else 0)
    
    # Get top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(Sales.units_sold).label('total_units'),
        func.sum(Sales.units_sold * Product.selling_price_per_unit).label('total_revenue')
    ).join(
        Sales, Sales.product_id == Product.id
    ).filter(
        Product.user_id == current_user.id,
        Sales.month >= twelve_months_ago
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(Sales.units_sold).desc()
    ).limit(5).all()
    
    return jsonify({
        'months': months,
        'units': units,
        'revenue': revenue,
        'top_products': [{
            'name': name,
            'units': int(total_units or 0),
            'revenue': float(total_revenue or 0)
        } for name, total_units, total_revenue in top_products]
    })

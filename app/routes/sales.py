# app/routes/sales.py

from datetime import datetime, timedelta
import logging

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func

from app import db
from app.forms import SalesForm
from app.models import Product, Sales
from app.security import SecurityUtils
from app.utils.decorators import rate_limit
from app.validators import check_security, sanitize_input

logger = logging.getLogger(__name__)
sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


def _wants_json_response() -> bool:
    """Return True when the request expects a JSON payload."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    accept = request.accept_mimetypes
    return bool(accept and accept.best == 'application/json')


def _json_form_errors(form: SalesForm):
    return {field: errors for field, errors in form.errors.items() if errors}


@sales_bp.route('/', methods=['GET', 'POST'])
@login_required
@rate_limit(max_calls=20, period=60)
def manage_sales():
    """View and create monthly sales records."""
    form = SalesForm(user_id=current_user.id)
    wants_json = _wants_json_response()

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                customer_name = sanitize_input(form.customer_name.data or '', 'html')
                notes = sanitize_input(form.notes.data or '', 'html')

                if check_security(customer_name, 'all') or check_security(notes, 'all'):
                    SecurityUtils.log_security_event('sales_security_issue', {
                        'user_id': current_user.id,
                        'customer_name': customer_name,
                        'notes': notes,
                        'ip': request.remote_addr
                    }, 'warning')
                    message = 'Invalid input detected in sales data.'
                    if wants_json:
                        return jsonify({'status': 'error', 'message': message}), 400
                    flash(message, 'danger')
                    return redirect(url_for('sales.manage_sales'))

                product = Product.query.filter_by(id=form.product_id.data, user_id=current_user.id).first()
                if not product:
                    SecurityUtils.log_security_event('unauthorized_product_sale', {
                        'user_id': current_user.id,
                        'product_id': form.product_id.data,
                        'ip': request.remote_addr
                    }, 'warning')
                    message = 'Invalid product selected.'
                    if wants_json:
                        return jsonify({'status': 'error', 'message': message}), 400
                    flash(message, 'danger')
                    return redirect(url_for('sales.manage_sales'))

                units_sold = int(form.units_sold.data or 0)
                unit_price = float(product.selling_price_per_unit or 0)
                month_value = form.date.data.strftime('%Y-%m')

                sale = Sales(
                    product_id=product.id,
                    user_id=current_user.id,
                    month=month_value,
                    units_sold=units_sold,
                    total_revenue=round(units_sold * unit_price, 2),
                    customer_count=1 if customer_name else 0
                )
                db.session.add(sale)
                db.session.commit()

                SecurityUtils.log_security_event('sale_recorded', {
                    'user_id': current_user.id,
                    'sale_id': sale.id,
                    'product_id': product.id,
                    'units_sold': units_sold,
                    'month': month_value,
                    'ip': request.remote_addr
                }, 'info')

                if wants_json:
                    return jsonify({
                        'status': 'success',
                        'message': 'Sale recorded successfully.',
                        'sale_id': sale.id
                    })

                flash('Sale recorded successfully!', 'success')
                return redirect(url_for('sales.manage_sales'))

            except Exception as exc:
                db.session.rollback()
                logger.error('Error saving sale: %s', exc, exc_info=True)
                if wants_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'An error occurred while saving the sale.'
                    }), 500
                flash('An error occurred while saving the sale.', 'danger')
        elif wants_json:
            return jsonify({
                'status': 'error',
                'message': 'Please correct the highlighted errors.',
                'errors': _json_form_errors(form)
            }), 400

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = max(1, min(per_page, 100))

    search = (request.args.get('search') or '').strip()
    start_date_input = (request.args.get('start_date') or '').strip()
    end_date_input = (request.args.get('end_date') or '').strip()
    product_id = request.args.get('product_id', type=int)

    base_query = db.session.query(Sales).join(Product, Product.id == Sales.product_id).filter(
        Sales.user_id == current_user.id
    )

    if search:
        like_pattern = f'%{search}%'
        base_query = base_query.filter(
            Product.name.ilike(like_pattern) |
            Sales.month.ilike(like_pattern)
        )

    if product_id:
        base_query = base_query.filter(Sales.product_id == product_id)

    if start_date_input:
        try:
            start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
            base_query = base_query.filter(Sales.month >= start_date.strftime('%Y-%m'))
        except ValueError:
            start_date_input = ''

    if end_date_input:
        try:
            end_date = datetime.strptime(end_date_input, '%Y-%m-%d').date()
            base_query = base_query.filter(Sales.month <= end_date.strftime('%Y-%m'))
        except ValueError:
            end_date_input = ''

    sales_query = base_query.with_entities(
        Sales,
        Product.name.label('product_name'),
        Product.selling_price_per_unit.label('unit_price')
    ).order_by(desc(Sales.month), desc(Sales.id))

    pagination = sales_query.paginate(page=page, per_page=per_page, error_out=False)
    sales = pagination.items

    summary_row = base_query.with_entities(
        func.coalesce(func.sum(Sales.units_sold), 0).label('total_sales'),
        func.coalesce(func.sum(Sales.total_revenue), 0).label('total_revenue'),
        func.count(func.distinct(Sales.product_id)).label('total_products')
    ).first()

    summary = {
        'total_sales': int(summary_row.total_sales or 0),
        'total_revenue': float(summary_row.total_revenue or 0),
        'total_products': int(summary_row.total_products or 0)
    }

    if wants_json:
        payload = []
        for sale, product_name, unit_price in sales:
            resolved_unit_price = float(unit_price or 0)
            resolved_total = float(sale.total_revenue or (resolved_unit_price * (sale.units_sold or 0)))
            payload.append({
                'id': sale.id,
                'date': f'{sale.month}-01',
                'month': sale.month,
                'product_name': product_name,
                'customer_name': '',
                'quantity': int(sale.units_sold or 0),
                'unit_price': resolved_unit_price,
                'total_amount': resolved_total,
                'notes': ''
            })

        return jsonify({
            'sales': payload,
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
        search=search,
        start_date=start_date_input,
        end_date=end_date_input,
        selected_product_id=product_id or ''
    )


@sales_bp.route('/edit/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def edit_sale(sale_id):
    """Edit an existing sale record."""
    sale = Sales.query.get_or_404(sale_id)

    if sale.user_id != current_user.id:
        abort(403)

    form = SalesForm(user_id=current_user.id)
    wants_json = _wants_json_response()

    if request.method == 'GET':
        form.product_id.data = sale.product_id
        form.date.data = datetime.strptime(f'{sale.month}-01', '%Y-%m-%d').date()
        form.units_sold.data = sale.units_sold

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                product = Product.query.filter_by(id=form.product_id.data, user_id=current_user.id).first()
                if not product:
                    message = 'Invalid product selected.'
                    if wants_json:
                        return jsonify({'status': 'error', 'message': message}), 400
                    flash(message, 'danger')
                    return redirect(url_for('sales.manage_sales'))

                units_sold = int(form.units_sold.data or 0)
                unit_price = float(product.selling_price_per_unit or 0)

                sale.product_id = product.id
                sale.month = form.date.data.strftime('%Y-%m')
                sale.units_sold = units_sold
                sale.total_revenue = round(units_sold * unit_price, 2)
                sale.customer_count = 1 if (form.customer_name.data or '').strip() else 0

                db.session.commit()

                if wants_json:
                    return jsonify({'status': 'success', 'message': 'Sale updated successfully.'})

                flash('Sale updated successfully!', 'success')
                return redirect(url_for('sales.manage_sales'))

            except Exception as exc:
                db.session.rollback()
                logger.error('Error updating sale %s: %s', sale_id, exc, exc_info=True)
                if wants_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'An error occurred while updating the sale.'
                    }), 500
                flash('An error occurred while updating the sale.', 'danger')
        elif wants_json:
            return jsonify({
                'status': 'error',
                'message': 'Please correct the highlighted errors.',
                'errors': _json_form_errors(form)
            }), 400

    return render_template('sales/edit_sale.html', form=form, sale=sale)


@sales_bp.route('/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    """Delete a sale record."""
    sale = Sales.query.get_or_404(sale_id)

    if sale.user_id != current_user.id:
        abort(403)

    wants_json = _wants_json_response()

    try:
        db.session.delete(sale)
        db.session.commit()

        if wants_json:
            return jsonify({'status': 'success', 'message': 'Sale deleted successfully!'})

        flash('Sale deleted successfully!', 'success')

    except Exception as exc:
        db.session.rollback()
        logger.error('Error deleting sale %s: %s', sale_id, exc, exc_info=True)

        if wants_json:
            return jsonify({
                'status': 'error',
                'message': 'An error occurred while deleting the sale.'
            }), 500

        flash('An error occurred while deleting the sale.', 'danger')

    return redirect(url_for('sales.manage_sales'))


@sales_bp.route('/api/summary')
@login_required
def sales_summary():
    """Get sales summary data for charts and dashboards."""
    twelve_months_ago = (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m')
    revenue_expr = func.coalesce(Sales.total_revenue, Sales.units_sold * Product.selling_price_per_unit)

    monthly_sales = db.session.query(
        Sales.month,
        func.sum(Sales.units_sold).label('total_units'),
        func.sum(revenue_expr).label('total_revenue')
    ).join(
        Product, Product.id == Sales.product_id
    ).filter(
        Sales.user_id == current_user.id,
        Sales.month >= twelve_months_ago
    ).group_by(
        Sales.month
    ).order_by(
        Sales.month
    ).all()

    months = []
    units = []
    revenue = []

    for month_data in monthly_sales:
        months.append(month_data.month)
        units.append(int(month_data.total_units or 0))
        revenue.append(float(month_data.total_revenue or 0))

    top_products = db.session.query(
        Product.name,
        func.sum(Sales.units_sold).label('total_units'),
        func.sum(revenue_expr).label('total_revenue')
    ).join(
        Sales, Sales.product_id == Product.id
    ).filter(
        Sales.user_id == current_user.id,
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

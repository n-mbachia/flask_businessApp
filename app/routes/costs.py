from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import or_, func
from flask_wtf.csrf import validate_csrf

from app import db
from app.models.costs import CostEntry, CostTypeEnum, CostClassification
from app.models.products import Product
from app.forms.cost_form import CostForm
from app.utils.decorators import handle_exceptions, rate_limit
from app.validators import sanitize_input, check_security
from app.security import SecurityUtils
import logging

logger = logging.getLogger(__name__)
costs_bp = Blueprint('costs', __name__, url_prefix='/costs')

def get_cost_filters():
    """Get common filter parameters for cost queries."""
    return {
        'cost_type': request.args.get('cost_type'),
        'classification': request.args.get('classification'),
        'product_id': request.args.get('product_id', type=int),
        'is_direct': request.args.get('is_direct', type=lambda x: x.lower() == 'true' if x else None),
        'is_tax_deductible': request.args.get('is_tax_deductible', type=lambda x: x.lower() == 'true' if x else None),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
    }

def apply_filters(query, filters):
    """Apply filter parameters to a cost query."""
    if filters['cost_type'] and filters['cost_type'] in [e.name for e in CostTypeEnum]:
        query = query.filter_by(cost_type=CostTypeEnum[filters['cost_type']])
    if filters['classification'] and filters['classification'] in [e.name for e in CostClassification]:
        query = query.filter_by(classification=CostClassification[filters['classification']])
    if filters['product_id']:
        query = query.filter_by(product_id=filters['product_id'])
    if filters['is_direct'] is not None:
        query = query.filter_by(is_direct=filters['is_direct'])
    if filters['is_tax_deductible'] is not None:
        query = query.filter_by(is_tax_deductible=filters['is_tax_deductible'])
    if filters['start_date']:
        query = query.filter(CostEntry.date >= datetime.strptime(filters['start_date'], '%Y-%m-%d').date())
    if filters['end_date']:
        query = query.filter(CostEntry.date <= datetime.strptime(filters['end_date'], '%Y-%m-%d').date())
    return query

@costs_bp.route('', methods=['GET', 'POST'])
@login_required
@handle_exceptions
@rate_limit(max_calls=20, period=60)
def manage_costs():
    """Manage cost entries with pagination and filtering."""
    form = CostForm(user_id=current_user.id, **request.args)
    filters = get_cost_filters()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Handle form submission
    if form.validate_on_submit():
        try:
            description = sanitize_input(form.description.data or '', 'html')
            if check_security(description, 'all'):
                SecurityUtils.log_security_event('cost_description_security_issue', {
                    'user_id': current_user.id,
                    'description': description,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid input detected.', 'danger')
                return redirect(url_for('costs.manage_costs', **request.args))

            if form.amount.data < 0 or form.amount.data > 10000000:
                SecurityUtils.log_security_event('invalid_cost_amount', {
                    'user_id': current_user.id,
                    'amount': form.amount.data,
                    'ip': request.remote_addr
                }, 'warning')
                flash('Invalid amount.', 'danger')
                return redirect(url_for('costs.manage_costs', **request.args))

            if form.is_direct.data and form.product_id.data:
                product = Product.query.filter_by(
                    id=form.product_id.data,
                    user_id=current_user.id
                ).first()
                if not product:
                    SecurityUtils.log_security_event('unauthorized_cost_product', {
                        'user_id': current_user.id,
                        'product_id': form.product_id.data,
                        'ip': request.remote_addr
                    }, 'warning')
                    flash('Invalid product.', 'danger')
                    return redirect(url_for('costs.manage_costs', **request.args))

            cost_entry = CostEntry(
                user_id=current_user.id,
                product_id=form.product_id.data if form.is_direct.data else None,
                date=form.date.data,
                amount=form.amount.data,
                cost_type=CostTypeEnum[form.cost_type.data.upper()],
                classification=CostClassification(form.classification.data),
                is_direct=form.is_direct.data,
                is_tax_deductible=form.is_tax_deductible.data,
                description=description,
                is_recurring=form.is_recurring.data,
                recurrence_frequency=form.recurrence_frequency.data if form.is_recurring.data else None
            )
            db.session.add(cost_entry)
            db.session.commit()
            flash('Cost added successfully!', 'success')
            return redirect(url_for('costs.manage_costs', **request.args))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding cost: {e}", exc_info=True)
            flash('Error adding cost. Please try again.', 'danger')

    # Build base query
    base_query = CostEntry.query.filter_by(user_id=current_user.id)
    filtered_query = apply_filters(base_query, filters)

    # Calculate totals (across all filtered entries, not just page)
    total_costs = filtered_query.with_entities(func.sum(CostEntry.amount)).scalar() or 0.0
    fixed_costs = filtered_query.filter_by(classification=CostClassification.FIXED).with_entities(func.sum(CostEntry.amount)).scalar() or 0.0
    variable_costs = filtered_query.filter_by(classification=CostClassification.VARIABLE).with_entities(func.sum(CostEntry.amount)).scalar() or 0.0
    semi_variable_costs = filtered_query.filter_by(classification=CostClassification.SEMI_VARIABLE).with_entities(func.sum(CostEntry.amount)).scalar() or 0.0

    # Paginated results
    costs = filtered_query.order_by(CostEntry.date.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Products for dropdown
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()

    return render_template(
        'costs/manage.html',
        form=form,
        costs=costs,
        CostType=CostTypeEnum,
        CostClassification=CostClassification,
        products=products,
        total_costs=total_costs,
        fixed_costs=fixed_costs,
        variable_costs=variable_costs,
        semi_variable_costs=semi_variable_costs,
        active_page='costs',
        **filters
    )

@costs_bp.route('/<int:cost_id>/edit', methods=['GET', 'POST'])
@login_required
@handle_exceptions
def edit_cost(cost_id):
    """Edit an existing cost entry."""
    cost = CostEntry.query.filter_by(id=cost_id, user_id=current_user.id).first_or_404()
    form = CostForm(user_id=current_user.id)

    if request.method == 'GET':
        form.cost_type.data = cost.cost_type.name
        form.classification.data = cost.classification.name
        form.product_id.data = cost.product_id if cost.is_direct else None
        form.date.data = cost.date
        form.amount.data = cost.amount
        form.is_direct.data = cost.is_direct
        form.is_tax_deductible.data = cost.is_tax_deductible
        form.description.data = cost.description
        form.is_recurring.data = cost.is_recurring
        form.recurrence_frequency.data = cost.recurrence_frequency

    if form.validate_on_submit():
        try:
            cost.product_id = form.product_id.data if form.is_direct.data else None
            cost.date = form.date.data
            cost.amount = form.amount.data
            cost.cost_type = CostTypeEnum[form.cost_type.data.upper()]
            cost.classification = CostClassification(form.classification.data)
            cost.is_direct = form.is_direct.data
            cost.is_tax_deductible = form.is_tax_deductible.data
            cost.description = sanitize_input(form.description.data or '', 'html')
            cost.is_recurring = form.is_recurring.data
            cost.recurrence_frequency = form.recurrence_frequency.data if form.is_recurring.data else None

            db.session.commit()
            flash('Cost updated successfully!', 'success')
            return redirect(url_for('costs.manage_costs', **request.args))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating cost: {e}", exc_info=True)
            flash('Error updating cost.', 'danger')

    return render_template(
        'costs/edit.html',
        form=form,
        cost=cost,
        CostType=CostTypeEnum,
        CostClassification=CostClassification
    )

@costs_bp.route('/<int:cost_id>/delete', methods=['POST'])
@login_required
@handle_exceptions
def delete_cost(cost_id):
    """Delete a cost entry (AJAX endpoint)."""
    try:
        # Validate CSRF token
        token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        validate_csrf(token)

        cost = CostEntry.query.filter_by(id=cost_id, user_id=current_user.id).first_or_404()
        db.session.delete(cost)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cost deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting cost {cost_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@costs_bp.route('/api/summary')
@login_required
def get_cost_summary():
    """API endpoint to get cost summary data for charts."""
    try:
        filters = get_cost_filters()
        base = CostEntry.query.filter(CostEntry.user_id == current_user.id)
        base = apply_filters(base, filters)

        # Group by type
        by_type = base.with_entities(
            CostEntry.cost_type,
            func.sum(CostEntry.amount).label('total')
        ).group_by(CostEntry.cost_type).all()

        # Group by classification
        by_class = base.with_entities(
            CostEntry.classification,
            func.sum(CostEntry.amount).label('total')
        ).group_by(CostEntry.classification).all()

        total_costs = base.with_entities(func.sum(CostEntry.amount)).scalar() or 0.0
        total_entries = base.count()

        type_data = [{
            'type': ct.value,
            'amount': float(total),
            'percentage': round((total / total_costs) * 100, 2) if total_costs > 0 else 0
        } for ct, total in by_type]

        class_data = [{
            'classification': cl.value,
            'amount': float(total),
            'percentage': round((total / total_costs) * 100, 2) if total_costs > 0 else 0
        } for cl, total in by_class]

        return jsonify({
            'success': True,
            'data': {
                'by_type': type_data,
                'by_classification': class_data,
                'total_costs': float(total_costs),
                'total_entries': total_entries
            }
        })
    except Exception as e:
        logger.error(f"Cost summary error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to generate summary'}), 500

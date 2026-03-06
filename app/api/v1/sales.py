"""Sales API endpoints for monthly sales snapshots."""

from datetime import datetime

from flask import request
from flask_login import current_user, login_required
from flask_restx import Namespace, Resource, fields

from app import db
from app.models import Product, Sales

ns = Namespace('sales', description='Sales operations')

sale_model = ns.model('SalesSnapshot', {
    'id': fields.Integer(description='Snapshot ID'),
    'product_id': fields.Integer(description='Product ID'),
    'product_name': fields.String(description='Product name'),
    'month': fields.String(description='Month in YYYY-MM format'),
    'units_sold': fields.Integer(description='Units sold in month'),
    'total_revenue': fields.Float(description='Total revenue for this snapshot'),
    'customer_count': fields.Integer(description='Number of customers represented'),
    'created_at': fields.DateTime(description='Created at timestamp'),
    'updated_at': fields.DateTime(description='Updated at timestamp')
})

create_sale_model = ns.model('CreateSalesSnapshot', {
    'product_id': fields.Integer(required=True, description='Product ID'),
    'month': fields.String(required=True, description='Month in YYYY-MM format'),
    'units_sold': fields.Integer(required=True, description='Units sold'),
    'customer_count': fields.Integer(required=False, description='Optional customer count')
})


def _serialize_sale(sale: Sales):
    return {
        'id': sale.id,
        'product_id': sale.product_id,
        'product_name': sale.product.name if sale.product else '',
        'month': sale.month,
        'units_sold': int(sale.units_sold or 0),
        'total_revenue': float(sale.total_revenue or 0),
        'customer_count': int(sale.customer_count or 0),
        'created_at': sale.created_at,
        'updated_at': sale.updated_at
    }


@ns.route('/')
class SaleList(Resource):
    @login_required
    @ns.marshal_list_with(sale_model)
    def get(self):
        """Get sales snapshots for the authenticated user."""
        month = request.args.get('month', '').strip()
        product_id = request.args.get('product_id', type=int)
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, min(request.args.get('per_page', 50, type=int), 200))

        query = Sales.query.filter_by(user_id=current_user.id)

        if month:
            query = query.filter(Sales.month == month)

        if product_id:
            query = query.filter(Sales.product_id == product_id)

        pagination = query.order_by(Sales.month.desc(), Sales.id.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return [_serialize_sale(sale) for sale in pagination.items]

    @login_required
    @ns.expect(create_sale_model)
    @ns.marshal_with(sale_model, code=201)
    def post(self):
        """Create a new monthly sales snapshot."""
        data = request.get_json(silent=True) or {}

        product_id = data.get('product_id')
        month = (data.get('month') or '').strip()
        units_sold = int(data.get('units_sold') or 0)
        customer_count = int(data.get('customer_count') or 0)

        if not product_id or not month:
            ns.abort(400, 'product_id and month are required')

        try:
            datetime.strptime(month, '%Y-%m')
        except ValueError:
            ns.abort(400, 'month must be in YYYY-MM format')

        if units_sold <= 0:
            ns.abort(400, 'units_sold must be greater than zero')

        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
        if not product:
            ns.abort(404, 'Product not found')

        snapshot = Sales(
            product_id=product.id,
            user_id=current_user.id,
            month=month,
            units_sold=units_sold,
            total_revenue=round(float(product.selling_price_per_unit or 0) * units_sold, 2),
            customer_count=max(customer_count, 0)
        )

        db.session.add(snapshot)
        db.session.commit()

        return _serialize_sale(snapshot), 201


@ns.route('/<int:sale_id>')
@ns.param('sale_id', 'The sales snapshot identifier')
@ns.response(404, 'Snapshot not found')
class SaleResource(Resource):
    @login_required
    @ns.marshal_with(sale_model)
    def get(self, sale_id):
        """Get a specific sales snapshot."""
        sale = Sales.query.get_or_404(sale_id)
        if sale.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to view this snapshot')
        return _serialize_sale(sale)

    @login_required
    @ns.response(204, 'Snapshot deleted')
    def delete(self, sale_id):
        """Delete a specific sales snapshot."""
        sale = Sales.query.get_or_404(sale_id)
        if sale.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to delete this snapshot')

        db.session.delete(sale)
        db.session.commit()
        return '', 204

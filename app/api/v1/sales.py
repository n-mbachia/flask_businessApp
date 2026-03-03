"""
Sales API endpoints.

This module contains all sales-related API endpoints.
"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_login import login_required, current_user

# Create namespace
ns = Namespace('sales', description='Sales operations')

# Response models
sale_item_model = ns.model('SaleItem', {
    'id': fields.Integer(description='Sale item ID'),
    'product_id': fields.Integer(description='Product ID'),
    'quantity': fields.Integer(description='Quantity sold'),
    'unit_price': fields.Float(description='Price per unit'),
    'total_price': fields.Float(description='Total price')
})

sale_model = ns.model('Sale', {
    'id': fields.Integer(description='Sale ID'),
    'sale_date': fields.DateTime(description='Date of sale'),
    'total_amount': fields.Float(description='Total sale amount'),
    'customer_id': fields.Integer(description='Customer ID'),
    'user_id': fields.Integer(description='User who made the sale'),
    'items': fields.List(fields.Nested(sale_item_model), description='Sale items')
})

@ns.route('/')
class SaleList(Resource):
    @ns.marshal_list_with(sale_model)
    @login_required
    def get(self):
        """Get all sales."""
        from app.models import Sale
        return Sale.query.filter_by(user_id=current_user.id).all()
    
    @ns.expect(sale_model)
    @ns.marshal_with(sale_model, code=201)
    @login_required
    def post(self):
        """Create a new sale."""
        from app.models import Sale, SaleItem, db
        
        data = request.get_json()
        sale = Sale(
            customer_id=data['customer_id'],
            user_id=current_user.id,
            total_amount=data['total_amount']
        )
        
        db.session.add(sale)
        db.session.flush()  # To get the sale ID
        
        # Add sale items
        for item_data in data.get('items', []):
            item = SaleItem(
                sale_id=sale.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            db.session.add(item)
        
        db.session.commit()
        return sale, 201

@ns.route('/<int:sale_id>')
@ns.param('sale_id', 'The sale identifier')
@ns.response(404, 'Sale not found')
class SaleResource(Resource):
    @ns.marshal_with(sale_model)
    @login_required
    def get(self, sale_id):
        """Get a specific sale."""
        from app.models import Sale
        sale = Sale.query.get_or_404(sale_id)
        if sale.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to view this sale')
        return sale
    
    @ns.response(204, 'Sale deleted')
    @login_required
    def delete(self, sale_id):
        """Delete a sale."""
        from app.models import Sale, db
        
        sale = Sale.query.get_or_404(sale_id)
        if sale.user_id != current_user.id:
            ns.abort(403, 'You do not have permission to delete this sale')
            
        db.session.delete(sale)
        db.session.commit()
        return '', 204

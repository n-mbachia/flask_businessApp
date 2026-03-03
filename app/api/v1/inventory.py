"""
Inventory API endpoints.

This module contains all inventory-related API endpoints.
"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_login import login_required, current_user

# Create namespace
ns = Namespace('inventory', description='Inventory operations')

# Response models
inventory_item_model = ns.model('InventoryItem', {
    'id': fields.Integer(description='Inventory item ID'),
    'product_id': fields.Integer(description='Product ID'),
    'quantity': fields.Integer(description='Current quantity in stock'),
    'reorder_level': fields.Integer(description='Reorder level'),
    'last_updated': fields.DateTime(description='Last updated timestamp')
})

@ns.route('/')
class InventoryList(Resource):
    @ns.marshal_list_with(inventory_item_model)
    @login_required
    def get(self):
        """Get all inventory items."""
        from app.models import InventoryItem
        return InventoryItem.query.all()
    
    @ns.expect(inventory_item_model)
    @ns.marshal_with(inventory_item_model, code=201)
    @login_required
    def post(self):
        """Add a new inventory item."""
        from app.models import InventoryItem, db
        
        data = request.get_json()
        item = InventoryItem(
            product_id=data['product_id'],
            quantity=data['quantity'],
            reorder_level=data.get('reorder_level', 10)
        )
        
        db.session.add(item)
        db.session.commit()
        return item, 201

@ns.route('/<int:item_id>')
@ns.param('item_id', 'The inventory item identifier')
@ns.response(404, 'Inventory item not found')
class InventoryItemResource(Resource):
    @ns.marshal_with(inventory_item_model)
    @login_required
    def get(self, item_id):
        """Get a specific inventory item."""
        from app.models import InventoryItem
        return InventoryItem.query.get_or_404(item_id)
    
    @ns.expect(inventory_item_model)
    @ns.marshal_with(inventory_item_model)
    @login_required
    def put(self, item_id):
        """Update an inventory item."""
        from app.models import InventoryItem, db
        
        item = InventoryItem.query.get_or_404(item_id)
        data = request.get_json()
        
        # Update item fields
        if 'quantity' in data:
            item.quantity = data['quantity']
        if 'reorder_level' in data:
            item.reorder_level = data['reorder_level']
        
        db.session.commit()
        return item
    
    @ns.response(204, 'Inventory item deleted')
    @login_required
    def delete(self, item_id):
        """Delete an inventory item."""
        from app.models import InventoryItem, db
        
        item = InventoryItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        return '', 204

@ns.route('/low-stock')
class LowStockList(Resource):
    @ns.marshal_list_with(inventory_item_model)
    @login_required
    def get(self):
        """Get all inventory items below reorder level."""
        from app.models import InventoryItem
        return InventoryItem.query.filter(
            InventoryItem.quantity <= InventoryItem.reorder_level
        ).all()

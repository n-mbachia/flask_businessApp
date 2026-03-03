# app/schemas.py
from marshmallow import Schema, fields, validate

class ProductSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    cogs_per_unit = fields.Float(required=True)
    selling_price_per_unit = fields.Float(required=True)
    margin_threshold = fields.Float(allow_none=True)

class SalesSchema(Schema):
    product_id = fields.Int(required=True)
    month = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}$'))
    units_sold = fields.Int(required=True, validate=validate.Range(min=0))

"""Utility helpers for working with products."""

import re
import uuid

from app.models import Product


def generate_sku(product_name: str, user_id: int) -> str:
    """Return a unique SKU for a user/product combination."""
    clean_name = re.sub(r'[^A-Z0-9]', '', product_name.upper())
    prefix = clean_name[:6] if clean_name else 'PROD'
    user_prefix = f"U{user_id % 1000:03d}"
    base = f"{prefix}-{user_prefix}-{uuid.uuid4().hex[:8].upper()}"
    sku = base
    counter = 1

    while Product.query.filter_by(sku=sku).first():
        sku = f"{base}-{counter}"
        counter += 1
        if counter > 100:
            sku = f"PROD-{user_prefix}-{uuid.uuid4().hex[:8].upper()}"
            break

    return sku

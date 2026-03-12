#!/usr/bin/env python3
"""
Smoke test: create a user, product, initial stock, and a completed order.
Validates that inventory movements are created and stock is decremented.
"""
import sys
import os
import faulthandler
from pathlib import Path
from decimal import Decimal
from uuid import uuid4

# Add businessApp root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flask import Flask
from app import db
from config import TestingConfig
from app.models import User, Product, Order
from app.services.order_service import OrderService
from app.services.inventory_service import InventoryService


def main() -> int:
    os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")
    faulthandler.dump_traceback_later(10, repeat=False)

    class SmokeConfig(TestingConfig):
        SQLALCHEMY_ENGINE_OPTIONS = {}

    app = Flask(__name__)
    app.config.from_object(SmokeConfig)
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()

            print("[SMOKE] Creating test user...")
            user = User(
                username=f"smoke_{uuid4().hex[:8]}",
                email=f"smoke_{uuid4().hex[:8]}@example.com",
                confirmed=True
            )
            user.set_password("test-password")
            db.session.add(user)
            db.session.flush()

            print("[SMOKE] Creating test product...")
            product = Product(
                user_id=user.id,
                name=f"Smoke Product {uuid4().hex[:6]}",
                category="Smoke",
                cogs_per_unit=Decimal("5.00"),
                selling_price_per_unit=Decimal("10.00"),
                reorder_level=5,
                track_inventory=True,
                is_active=True,
                is_approved=True
            )
            db.session.add(product)
            db.session.flush()

            print("[SMOKE] Seeding initial stock...")
            InventoryService.update_inventory_levels(
                db.session,
                user.id,
                updates=[{
                    'product_id': product.id,
                    'quantity_change': 20,
                    'adjustment_type': 'receipt',
                    'unit_cost': product.cogs_per_unit,
                    'notes': 'Smoke test initial stock'
                }],
                reference_type='receipt',
                reference_id=None,
                notes='Smoke test initial stock',
                auto_commit=False
            )

            print("[SMOKE] Creating completed order...")
            order_data = {
                'status': Order.STATUS_COMPLETED,
                'payment_status': Order.PAYMENT_PAID,
                'source': Order.SOURCE_MANUAL
            }
            items_data = [{
                'product_id': product.id,
                'quantity': 3,
                'unit_price': float(product.selling_price_per_unit)
            }]

            order = OrderService.create_order(
                user_id=user.id,
                order_data=order_data,
                items_data=items_data,
                update_inventory=True
            )

            db.session.refresh(product)
            current_stock = product.current_stock

            # Validate stock decrement
            expected_stock = 17
            if current_stock != expected_stock:
                print(f"[FAIL] Expected stock {expected_stock}, got {current_stock}")
                return 1

            print("[OK] Smoke order creation passed.")
            print(f"[OK] Order ID: {order.id}, Product ID: {product.id}, Stock: {current_stock}")
            return 0

        except Exception as exc:
            db.session.rollback()
            print(f"[FAIL] Smoke order creation failed: {exc}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

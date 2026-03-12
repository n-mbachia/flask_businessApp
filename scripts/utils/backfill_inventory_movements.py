#!/usr/bin/env python3
"""
Backfill InventoryMovement records from InventoryLog and quantity_available.
Use --dry-run to preview changes.
"""
import sys
import os
from pathlib import Path
import argparse

# Add businessApp root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import create_app, db
from app.models import InventoryLog, InventoryMovement, Product
from app.services.inventory_service import InventoryService


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill inventory movements from logs.")
    parser.add_argument('--config', default='default', help='Config name (default, development, testing)')
    parser.add_argument('--dry-run', action='store_true', help='Print changes without committing')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of logs to process (0 = no limit)')
    return parser.parse_args()


def movement_exists(product_id, reference_type, reference_id, quantity):
    query = InventoryMovement.query.filter(
        InventoryMovement.product_id == product_id,
        InventoryMovement.reference_type == reference_type,
        InventoryMovement.reference_id == reference_id
    )
    if quantity is not None:
        query = query.filter(InventoryMovement.quantity == quantity)
    return db.session.query(query.exists()).scalar()


def backfill_logs(dry_run=False, limit=0):
    query = InventoryLog.query.order_by(InventoryLog.created_at.asc())
    if limit and limit > 0:
        query = query.limit(limit)

    created = 0
    skipped = 0

    for log in query.all():
        quantity = int(round(abs(log.quantity_change or 0)))
        if quantity == 0:
            skipped += 1
            continue

        if movement_exists(log.product_id, log.reference_type, log.reference_id, quantity):
            skipped += 1
            continue

        movement_type = InventoryService._resolve_movement_type(
            log.reference_type,
            log.quantity_change
        )

        movement = InventoryMovement(
            product_id=log.product_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=log.unit_cost,
            reference_id=log.reference_id,
            reference_type=log.reference_type,
            notes=f"Backfill from InventoryLog {log.id}: {log.notes or ''}".strip()
        )
        db.session.add(movement)
        created += 1

        if dry_run:
            db.session.rollback()

    return created, skipped


def backfill_opening_balances(dry_run=False):
    created = 0
    for product in Product.query.filter_by(is_active=True).all():
        if not product.track_inventory:
            continue
        has_movements = db.session.query(
            InventoryMovement.query.filter_by(product_id=product.id).exists()
        ).scalar()
        if has_movements:
            continue

        available = int(round(product.quantity_available or 0))
        if available <= 0:
            continue

        movement = InventoryMovement(
            product_id=product.id,
            movement_type='receipt',
            quantity=available,
            unit_cost=product.cogs_per_unit,
            reference_id=None,
            reference_type='migration',
            notes='Opening balance from quantity_available'
        )
        db.session.add(movement)
        created += 1

        if dry_run:
            db.session.rollback()

    return created


def main() -> int:
    os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")
    args = parse_args()
    app = create_app(args.config)
    with app.app_context():
        try:
            created_logs, skipped_logs = backfill_logs(dry_run=args.dry_run, limit=args.limit)
            created_opening = backfill_opening_balances(dry_run=args.dry_run)

            if args.dry_run:
                print(f"[DRY RUN] Movements to create from logs: {created_logs}, skipped: {skipped_logs}")
                print(f"[DRY RUN] Opening balance movements: {created_opening}")
                return 0

            db.session.commit()
            print(f"[OK] Created movements from logs: {created_logs}, skipped: {skipped_logs}")
            print(f"[OK] Created opening balance movements: {created_opening}")
            return 0

        except Exception as exc:
            db.session.rollback()
            print(f"[FAIL] Backfill failed: {exc}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

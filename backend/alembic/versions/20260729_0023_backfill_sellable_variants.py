"""backfill sellable variants for legacy product stock

Revision ID: 20260729_0023
Revises: 20260729_0022
Create Date: 2026-07-28
"""

from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision = "20260729_0023"
down_revision = "20260729_0022"
branch_labels = None
depends_on = None


def _token(value: object) -> str:
    return "".join(character for character in str(value or "").upper() if character.isalnum()) or "STD"


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("""
        SELECT product.id, product.store_id, product.name, product.size, product.color,
               product.mrp, product.selling_price, product.purchase_price,
               COALESCE(inventory.current_stock, product.current_stock, 0) AS current_stock,
               COUNT(variant.id) AS variant_count
        FROM products AS product
        LEFT JOIN product_inventory AS inventory
          ON inventory.product_id = product.id AND inventory.store_id = product.store_id
        LEFT JOIN product_variants AS variant ON variant.product_id = product.id
        WHERE product.store_id IS NOT NULL
        GROUP BY product.id, inventory.current_stock
    """)).mappings().all()
    for row in rows:
        if row["variant_count"] != 0:
            continue
        stock = int(row["current_stock"] or 0)
        mrp = Decimal(row["mrp"] or row["selling_price"] or 0)
        price = Decimal(row["selling_price"] or 0)
        cost = Decimal(row["purchase_price"] or 0)
        variant_id = uuid4()
        sku = f"LEG-{str(row['id'])[:8].upper()}-{_token(row['size'])}-{mrp.quantize(Decimal('1'))}"
        bind.execute(sa.text("""
            INSERT INTO product_variants (
                id, store_id, product_id, color, size, style_code, internal_sku, barcode,
                identity_key, mrp, selling_price, last_purchase_cost, average_cost,
                current_stock, classification_review_required, is_active, created_at, updated_at
            ) VALUES (
                :id, :store_id, :product_id, :color, :size, 'LEGACY', :sku, :barcode,
                :identity_key, :mrp, :price, :cost, :cost, :stock, true, true, now(), now()
            )
        """), {
            "id": variant_id, "store_id": row["store_id"], "product_id": row["id"],
            "color": row["color"], "size": row["size"], "sku": sku,
            "barcode": f"LEG{uuid4().hex[:16].upper()}",
            "identity_key": f"{row['id']}|legacy|{mrp:.2f}|{price:.2f}",
            "mrp": mrp, "price": price, "cost": cost, "stock": stock,
        })
        if stock:
            bind.execute(sa.text("""
                INSERT INTO inventory_cost_lots (
                    id, store_id, product_variant_id, received_quantity, remaining_quantity,
                    unit_purchase_cost, allocated_landed_cost, effective_unit_cost,
                    received_date, lot_reference, created_at
                ) VALUES (:id, :store_id, :variant_id, :stock, :stock, :cost, 0, :cost, now(), 'Legacy stock migration', now())
            """), {"id": uuid4(), "store_id": row["store_id"], "variant_id": variant_id, "stock": stock, "cost": cost})


def downgrade() -> None:
    # Backfilled variants are deliberately retained to preserve migrated stock history.
    pass

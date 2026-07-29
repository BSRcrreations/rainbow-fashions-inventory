"""allocate legacy aggregate stock to sellable variants

Revision ID: 20260728_0022
Revises: 20260728_0021
Create Date: 2026-07-28
"""

from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision = "20260728_0022"
down_revision = "20260728_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move only unallocated legacy aggregate stock into existing variants.

    The old schema retained stock only on a product. With no historical per-size
    allocation available, balances are evenly assigned in stable variant order
    and marked for review. Product and store inventory totals are not changed.
    """
    bind = op.get_bind()
    products = bind.execute(sa.text("""
        SELECT product.id, product.store_id, product.purchase_price,
               COALESCE(inventory.current_stock, product.current_stock, 0) AS aggregate_stock,
               COALESCE(SUM(variant.current_stock), 0) AS variant_stock
        FROM products AS product
        LEFT JOIN product_inventory AS inventory
          ON inventory.product_id = product.id AND inventory.store_id = product.store_id
        JOIN product_variants AS variant ON variant.product_id = product.id
        WHERE product.store_id IS NOT NULL
        GROUP BY product.id, inventory.current_stock
        HAVING COALESCE(inventory.current_stock, product.current_stock, 0) > COALESCE(SUM(variant.current_stock), 0)
    """)).mappings().all()
    for product in products:
        remaining = int(product["aggregate_stock"] - product["variant_stock"])
        variants = bind.execute(sa.text("""
            SELECT id FROM product_variants
            WHERE product_id = :product_id AND current_stock = 0
            ORDER BY created_at, id
        """), {"product_id": product["id"]}).mappings().all()
        if not variants:
            continue
        allocation, remainder = divmod(remaining, len(variants))
        for index, variant in enumerate(variants):
            quantity = allocation + (1 if index < remainder else 0)
            if not quantity:
                continue
            cost = Decimal(product["purchase_price"] or 0)
            bind.execute(sa.text("""
                UPDATE product_variants
                SET current_stock = current_stock + :quantity,
                    classification_review_required = true,
                    last_purchase_cost = :cost,
                    average_cost = :cost,
                    updated_at = now()
                WHERE id = :variant_id
            """), {"variant_id": variant["id"], "quantity": quantity, "cost": cost})
            bind.execute(sa.text("""
                INSERT INTO inventory_cost_lots (
                    id, store_id, product_variant_id, received_quantity, remaining_quantity,
                    unit_purchase_cost, allocated_landed_cost, effective_unit_cost,
                    received_date, lot_reference, created_at
                ) VALUES (:id, :store_id, :variant_id, :quantity, :quantity, :cost, 0, :cost, now(), 'Legacy aggregate allocation', now())
            """), {
                "id": uuid4(), "store_id": product["store_id"], "variant_id": variant["id"],
                "quantity": quantity, "cost": cost,
            })


def downgrade() -> None:
    # Retain inferred allocations; they represent the migrated on-hand balance.
    pass

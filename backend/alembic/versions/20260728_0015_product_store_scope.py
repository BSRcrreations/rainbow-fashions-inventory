"""add explicit product store scope

Revision ID: 20260728_0015
Revises: 20260728_0014
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0015"
down_revision = "20260728_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="SET NULL")))
    op.create_index("ix_products_store_id", "products", ["store_id"])
    # Backfill only unambiguous records. Ambiguous or orphaned legacy products
    # remain unscoped and are deliberately ineligible for destructive actions.
    op.execute("""
        UPDATE products AS product
        SET store_id = scoped.store_id
        FROM (
            SELECT product_id, MIN(store_id::text)::uuid AS store_id
            FROM product_inventory
            GROUP BY product_id
            HAVING COUNT(DISTINCT store_id) = 1
        ) AS scoped
        WHERE product.id = scoped.product_id AND product.store_id IS NULL
    """)
    op.execute("""
        UPDATE products AS product
        SET store_id = scoped.store_id
        FROM (
            SELECT product_id, MIN(store_id::text)::uuid AS store_id
            FROM stock_history
            WHERE store_id IS NOT NULL
            GROUP BY product_id
            HAVING COUNT(DISTINCT store_id) = 1
        ) AS scoped
        WHERE product.id = scoped.product_id AND product.store_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_products_store_id", table_name="products")
    op.drop_column("products", "store_id")

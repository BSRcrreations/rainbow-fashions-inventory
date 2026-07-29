"""persist purchase classification and scope catalog records to stores

Revision ID: 20260728_0013_classification
Revises: 20260727_0012
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0013_classification"
down_revision = "20260727_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This application began as a single-store catalog. Refuse an ambiguous
    # multistore backfill instead of silently exposing a shared catalog.
    op.execute("""
        DO $$ BEGIN
          IF (SELECT count(*) FROM stores) = 0 THEN
            RAISE EXCEPTION 'Cannot scope catalog records without a store';
          END IF;
        END $$;
    """)
    for table in ("categories", "brands", "subcategories"):
        op.add_column(table, sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.execute(f"UPDATE {table} SET store_id = (SELECT id FROM stores ORDER BY created_at, id LIMIT 1) WHERE store_id IS NULL")
        op.create_foreign_key(f"fk_{table}_store_id", table, "stores", ["store_id"], ["id"], ondelete="CASCADE" if table != "products" else "RESTRICT")
        op.create_index(f"ix_{table}_store_id", table, ["store_id"])
        op.alter_column(table, "store_id", nullable=False)

    op.drop_constraint("uq_categories_name", "categories", type_="unique")
    op.create_unique_constraint("uq_categories_store_name", "categories", ["store_id", "name"])
    op.drop_constraint("uq_brands_category_name", "brands", type_="unique")
    op.create_unique_constraint("uq_brands_store_category_name", "brands", ["store_id", "category_id", "name"])
    op.drop_constraint("uq_subcategories_category_name", "subcategories", type_="unique")
    op.create_unique_constraint("uq_subcategories_store_category_name", "subcategories", ["store_id", "category_id", "name"])
    op.add_column("products", sa.Column("description", sa.Text()))
    op.add_column("products", sa.Column("hsn_sac", sa.String(40)))
    op.add_column("products", sa.Column("unit", sa.String(40), server_default="Each", nullable=False))
    op.add_column("products", sa.Column("warehouse", sa.String(120)))

    op.add_column("purchase_items", sa.Column("proposed_product_name", sa.String(180)))
    op.add_column("purchase_items", sa.Column("selling_price", sa.Numeric(12, 2)))
    op.add_column("purchase_items", sa.Column("manufacturing_date", sa.Date()))
    op.add_column("purchase_items", sa.Column("create_new_product", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("purchase_items", sa.Column("variant_attributes", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("purchase_items", sa.Column("classification_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("purchase_items", sa.Column("classification_verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("purchase_items", sa.Column("classification_verified_at", sa.DateTime(timezone=True)))

    # Repair only unresolved draft/review labels that used the legacy
    # "category / product" format. The category remains a suggestion, never a
    # selected category_id, so staff must still review it.
    op.execute("""
        UPDATE purchase_items AS item
        SET category_name = NULLIF(btrim(split_part(item.product_name, '/', 1)), ''),
            proposed_product_name = NULLIF(btrim(split_part(item.product_name, '/', 2)), ''),
            product_name = NULLIF(btrim(split_part(item.product_name, '/', 2)), ''),
            create_new_product = TRUE,
            match_status = 'NEW_PRODUCT_REQUIRED'
        FROM purchases AS purchase
        WHERE purchase.id = item.purchase_id
          AND purchase.status IN ('DRAFT', 'REVIEWED')
          AND item.product_id IS NULL
          AND item.matched_product_id IS NULL
          AND position('/' IN item.product_name) > 0
    """)


def downgrade() -> None:
    op.drop_column("purchase_items", "classification_verified_at")
    op.drop_column("purchase_items", "classification_verified_by")
    op.drop_column("purchase_items", "classification_verified")
    op.drop_column("purchase_items", "variant_attributes")
    op.drop_column("purchase_items", "create_new_product")
    op.drop_column("purchase_items", "manufacturing_date")
    op.drop_column("purchase_items", "selling_price")
    op.drop_column("purchase_items", "proposed_product_name")
    for column in ("warehouse", "unit", "hsn_sac", "description"):
        op.drop_column("products", column)
    op.drop_constraint("uq_subcategories_store_category_name", "subcategories", type_="unique")
    op.create_unique_constraint("uq_subcategories_category_name", "subcategories", ["category_id", "name"])
    op.drop_constraint("uq_brands_store_category_name", "brands", type_="unique")
    op.create_unique_constraint("uq_brands_category_name", "brands", ["category_id", "name"])
    op.drop_constraint("uq_categories_store_name", "categories", type_="unique")
    op.create_unique_constraint("uq_categories_name", "categories", ["name"])
    for table in ("subcategories", "brands", "categories"):
        op.drop_index(f"ix_{table}_store_id", table_name=table)
        op.drop_constraint(f"fk_{table}_store_id", table, type_="foreignkey")
        op.drop_column(table, "store_id")

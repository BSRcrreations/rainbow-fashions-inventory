"""add barcode mappings and package conversion

Revision ID: 20260728_0024
Revises: 20260728_0023
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from uuid import uuid4


revision = "20260728_0024"
down_revision = "20260728_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "product_barcodes",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=False),
        sa.Column("barcode_type", sa.String(length=24), nullable=False, server_default="AUTO"),
        sa.Column("manufacturer_barcode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("package_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scan_unit", sa.String(length=24), nullable=False, server_default="PIECE"),
        sa.Column("inventory_unit", sa.String(length=24), nullable=False, server_default="PIECE"),
        sa.Column("base_unit_conversion", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mrp", sa.Numeric(12, 2)),
        sa.Column("default_selling_price", sa.Numeric(12, 2)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("store_id", "barcode", name="uq_product_barcodes_store_barcode"),
    )
    op.create_index("ix_product_barcodes_store_id", "product_barcodes", ["store_id"])
    op.create_index("ix_product_barcodes_barcode", "product_barcodes", ["barcode"])
    op.create_index("ix_product_barcodes_product_id", "product_barcodes", ["product_id"])
    op.create_index("ix_product_barcodes_product_variant_id", "product_barcodes", ["product_variant_id"])
    op.create_index("ix_product_barcodes_active", "product_barcodes", ["active"])
    op.create_table(
        "product_barcode_audits",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=False),
        sa.Column("old_product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="SET NULL")),
        sa.Column("new_product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=500)),
        sa.Column("changed_by", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.String(length=80)),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_product_barcode_audits_store_id", "product_barcode_audits", ["store_id"])
    op.create_index("ix_product_barcode_audits_barcode", "product_barcode_audits", ["barcode"])
    op.add_column("stock_scan_session_items", sa.Column("product_barcode_id", uuid, sa.ForeignKey("product_barcodes.id", ondelete="SET NULL")))
    op.add_column("stock_scan_session_items", sa.Column("package_quantity", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("stock_scan_session_items", sa.Column("base_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_stock_scan_session_items_product_barcode_id", "stock_scan_session_items", ["product_barcode_id"])
    op.drop_constraint("uq_stock_scan_session_variant", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", ["session_id", "product_barcode_id"])

    bind = op.get_bind()
    variants = bind.execute(sa.text("SELECT store_id, product_id, id, barcode, mrp, selling_price FROM product_variants")).mappings().all()
    for variant in variants:
        barcode_type = "EAN_13" if str(variant["barcode"]).isdigit() and len(str(variant["barcode"])) == 13 else "EAN_8" if str(variant["barcode"]).isdigit() and len(str(variant["barcode"])) == 8 else "CODE_128"
        bind.execute(sa.text("""
            INSERT INTO product_barcodes (id, store_id, product_id, product_variant_id, barcode, barcode_type, manufacturer_barcode, package_quantity, scan_unit, inventory_unit, base_unit_conversion, mrp, default_selling_price, active, verified, created_at, updated_at)
            VALUES (:id, :store_id, :product_id, :variant_id, :barcode, :barcode_type, false, 1, 'PIECE', 'PIECE', 1, :mrp, :selling_price, true, true, now(), now())
            ON CONFLICT (store_id, barcode) DO NOTHING
        """), {"id": uuid4(), "store_id": variant["store_id"], "product_id": variant["product_id"], "variant_id": variant["id"], "barcode": variant["barcode"], "barcode_type": barcode_type, "mrp": variant["mrp"], "selling_price": variant["selling_price"]})
    op.execute("UPDATE stock_scan_session_items SET base_quantity = scanned_quantity WHERE base_quantity = 0")
    op.alter_column("stock_scan_session_items", "package_quantity", server_default=None)
    op.alter_column("stock_scan_session_items", "base_quantity", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint("uq_stock_scan_session_variant", "stock_scan_session_items", ["session_id", "product_variant_id"])
    op.drop_index("ix_stock_scan_session_items_product_barcode_id", table_name="stock_scan_session_items")
    op.drop_column("stock_scan_session_items", "base_quantity")
    op.drop_column("stock_scan_session_items", "package_quantity")
    op.drop_column("stock_scan_session_items", "product_barcode_id")
    op.drop_table("product_barcode_audits")
    op.drop_table("product_barcodes")

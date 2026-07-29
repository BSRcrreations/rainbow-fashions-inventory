"""add stock scan onboarding defaults and barcode sale mode

Revision ID: 20260729_0028
Revises: 20260729_0027
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260729_0028"
down_revision = "20260729_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("product_barcodes", sa.Column("sale_mode", sa.String(length=24), nullable=False, server_default="PIECE_ONLY"))
    op.add_column("stock_scan_sessions", sa.Column("supplier_id", uuid, sa.ForeignKey("suppliers.id", ondelete="SET NULL")))
    op.add_column("stock_scan_sessions", sa.Column("default_category_id", uuid, sa.ForeignKey("categories.id", ondelete="SET NULL")))
    op.add_column("stock_scan_sessions", sa.Column("default_brand_id", uuid, sa.ForeignKey("brands.id", ondelete="SET NULL")))
    op.add_column("stock_scan_sessions", sa.Column("entry_date", sa.Date()))
    op.add_column("stock_scan_sessions", sa.Column("default_purchase_cost", sa.Numeric(12, 2)))
    op.add_column("stock_scan_sessions", sa.Column("default_selling_price", sa.Numeric(12, 2)))
    op.add_column("stock_scan_sessions", sa.Column("quick_post", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_stock_scan_sessions_supplier_id", "stock_scan_sessions", ["supplier_id"])
    op.create_index("ix_stock_scan_sessions_default_category_id", "stock_scan_sessions", ["default_category_id"])
    op.create_index("ix_stock_scan_sessions_default_brand_id", "stock_scan_sessions", ["default_brand_id"])
    op.alter_column("product_barcodes", "sale_mode", server_default=None)
    op.alter_column("stock_scan_sessions", "quick_post", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_stock_scan_sessions_default_brand_id", table_name="stock_scan_sessions")
    op.drop_index("ix_stock_scan_sessions_default_category_id", table_name="stock_scan_sessions")
    op.drop_index("ix_stock_scan_sessions_supplier_id", table_name="stock_scan_sessions")
    op.drop_column("stock_scan_sessions", "quick_post")
    op.drop_column("stock_scan_sessions", "default_selling_price")
    op.drop_column("stock_scan_sessions", "default_purchase_cost")
    op.drop_column("stock_scan_sessions", "entry_date")
    op.drop_column("stock_scan_sessions", "default_brand_id")
    op.drop_column("stock_scan_sessions", "default_category_id")
    op.drop_column("stock_scan_sessions", "supplier_id")
    op.drop_column("product_barcodes", "sale_mode")

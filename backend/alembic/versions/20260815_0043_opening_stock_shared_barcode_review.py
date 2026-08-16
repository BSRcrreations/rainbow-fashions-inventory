"""add owner-reviewed opening-stock shared barcode groups

Revision ID: 20260815_0043
Revises: 20260814_0042
Create Date: 2026-08-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260815_0043"
down_revision = "20260814_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("opening_stock_import_barcode_groups", sa.Column("id", uuid, primary_key=True), sa.Column("opening_stock_import_id", uuid, sa.ForeignKey("opening_stock_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("barcode", sa.String(80), nullable=False), sa.Column("classification", sa.String(40), nullable=False), sa.Column("decision", sa.String(40), nullable=False, server_default="PENDING"), sa.Column("matched_product_id", uuid, sa.ForeignKey("products.id", ondelete="SET NULL")), sa.Column("summary_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("reviewed_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("opening_stock_import_id", "barcode", name="uq_opening_stock_import_group_barcode"))
    op.create_index("ix_opening_stock_import_barcode_groups_opening_stock_import_id", "opening_stock_import_barcode_groups", ["opening_stock_import_id"])
    op.add_column("opening_stock_import_rows", sa.Column("barcode_group_id", uuid, sa.ForeignKey("opening_stock_import_barcode_groups.id", ondelete="SET NULL")))
    op.create_index("ix_opening_stock_import_rows_barcode_group_id", "opening_stock_import_rows", ["barcode_group_id"])


def downgrade() -> None:
    op.drop_index("ix_opening_stock_import_rows_barcode_group_id", table_name="opening_stock_import_rows")
    op.drop_column("opening_stock_import_rows", "barcode_group_id")
    op.drop_index("ix_opening_stock_import_barcode_groups_opening_stock_import_id", table_name="opening_stock_import_barcode_groups")
    op.drop_table("opening_stock_import_barcode_groups")

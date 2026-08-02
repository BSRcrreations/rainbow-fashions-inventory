"""link corrective stock movements to immutable originals

Revision ID: 20260802_0033
Revises: 20260730_0032
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260802_0033"
down_revision = "20260730_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stock_history", sa.Column("correction_of_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("stock_history", sa.Column("correction_reason", sa.String(length=80), nullable=True))
    op.add_column("stock_history", sa.Column("correction_notes", sa.String(length=2000), nullable=True))
    op.create_foreign_key("fk_stock_history_correction_of", "stock_history", "stock_history", ["correction_of_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_stock_history_correction_of_id", "stock_history", ["correction_of_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_history_correction_of_id", table_name="stock_history")
    op.drop_constraint("fk_stock_history_correction_of", "stock_history", type_="foreignkey")
    op.drop_column("stock_history", "correction_notes")
    op.drop_column("stock_history", "correction_reason")
    op.drop_column("stock_history", "correction_of_id")

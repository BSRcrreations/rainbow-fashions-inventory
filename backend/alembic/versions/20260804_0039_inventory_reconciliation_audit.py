"""Add immutable audit evidence for reconciliation aggregate repairs."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260804_0039"
down_revision = "20260804_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("inventory_reconciliation_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False), sa.Column("request_id", sa.String(120)), sa.Column("action", sa.String(40), nullable=False, server_default="COMPATIBILITY_AGGREGATE_REPAIR"),
        sa.Column("before_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("after_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inventory_reconciliation_audits_store_id", "inventory_reconciliation_audits", ["store_id"])
    op.create_index("ix_inventory_reconciliation_audits_product_id", "inventory_reconciliation_audits", ["product_id"])
    op.create_index("ix_inventory_reconciliation_audits_idempotency_key", "inventory_reconciliation_audits", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("inventory_reconciliation_audits")

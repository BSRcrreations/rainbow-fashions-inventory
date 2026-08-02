"""add owner stock reset audit trail

Revision ID: 20260802_0035
Revises: 20260802_0034
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260802_0035"
down_revision = "20260802_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'STOCK_RESET_OUT'")
    op.add_column("stock_history", sa.Column("request_id", sa.String(length=120), nullable=True))
    op.create_index("ix_stock_history_request_id", "stock_history", ["request_id"])
    op.create_table(
        "stock_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("user_role", sa.String(length=32)),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL")),
        sa.Column("previous_quantity", sa.Integer()),
        sa.Column("adjustment_quantity", sa.Integer()),
        sa.Column("resulting_quantity", sa.Integer()),
        sa.Column("request_id", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_stock_audit_events_event_type", "stock_audit_events", ["event_type"])
    op.create_index("ix_stock_audit_events_store_id", "stock_audit_events", ["store_id"])
    op.create_index("ix_stock_audit_events_user_id", "stock_audit_events", ["user_id"])
    op.create_index("ix_stock_audit_events_product_id", "stock_audit_events", ["product_id"])
    op.create_index("ix_stock_audit_events_product_variant_id", "stock_audit_events", ["product_variant_id"])
    op.create_index("ix_stock_audit_events_request_id", "stock_audit_events", ["request_id"])
    op.create_index("ix_stock_audit_events_created_at", "stock_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_audit_events_created_at", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_request_id", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_product_variant_id", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_product_id", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_user_id", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_store_id", table_name="stock_audit_events")
    op.drop_index("ix_stock_audit_events_event_type", table_name="stock_audit_events")
    op.drop_table("stock_audit_events")
    op.drop_index("ix_stock_history_request_id", table_name="stock_history")
    op.drop_column("stock_history", "request_id")

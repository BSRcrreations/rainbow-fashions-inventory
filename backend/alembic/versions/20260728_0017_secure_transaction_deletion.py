"""add secure owner-confirmed transaction deletion controls

Revision ID: 20260728_0017
Revises: 20260728_0016
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0017"
down_revision = "20260728_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE purchase_status ADD VALUE IF NOT EXISTS 'VOIDED'")
    op.execute("ALTER TYPE sale_status ADD VALUE IF NOT EXISTS 'DRAFT'")
    op.execute("ALTER TYPE sale_status ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'PURCHASE_VOID'")
    op.create_table(
        "store_security_settings",
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("delete_password_hash", sa.String()),
        sa.Column("require_password_for_sale_delete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_password_for_purchase_delete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "delete_password_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_delete_password_attempts_store_id", "delete_password_attempts", ["store_id"])
    op.create_index("ix_delete_password_attempts_user_id", "delete_password_attempts", ["user_id"])
    op.create_index("ix_delete_password_attempts_attempted_at", "delete_password_attempts", ["attempted_at"])
    op.create_table(
        "destructive_action_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("user_role", sa.String(32)), sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(32)), sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reference", sa.String(180)), sa.Column("original_status", sa.String(40)), sa.Column("final_action", sa.String(40)),
        sa.Column("record_counts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reversal_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("request_id", sa.String(80), nullable=False), sa.Column("client_ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    for name, columns in (("ix_destructive_action_audits_store_id", ["store_id"]), ("ix_destructive_action_audits_user_id", ["user_id"]), ("ix_destructive_action_audits_event_type", ["event_type"]), ("ix_destructive_action_audits_entity_id", ["entity_id"]), ("ix_destructive_action_audits_request_id", ["request_id"])):
        op.create_index(name, "destructive_action_audits", columns)
    op.create_table(
        "destructive_idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False), sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False), sa.Column("response_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("store_id", "user_id", "action", "idempotency_key", name="uq_destructive_idempotency"),
    )


def downgrade() -> None:
    op.drop_table("destructive_idempotency_records")
    op.drop_table("destructive_action_audits")
    op.drop_table("delete_password_attempts")
    op.drop_table("store_security_settings")

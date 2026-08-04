from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260803_0038"
down_revision = "20260803_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_update_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("changed_by_role", sa.String(length=40), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("change_source", sa.String(length=40), nullable=False),
        sa.Column("before_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("after_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("store_id", "product_id", "changed_by", "request_id", "created_at"):
        op.create_index(f"ix_product_update_audits_{column}", "product_update_audits", [column])


def downgrade() -> None:
    op.drop_table("product_update_audits")

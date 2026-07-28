"""add safe product bulk deletion controls

Revision ID: 20260728_0014
Revises: 20260728_0013
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0014"
down_revision = "20260728_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("is_test_data", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_products_is_test_data", "products", ["is_test_data"])
    op.add_column("stores", sa.Column("allow_test_data_purge", sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_table(
        "product_deletion_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("delete_mode", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("product_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deleted_record_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("performed_by_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_product_deletion_audits_store_id", "product_deletion_audits", ["store_id"])
    op.create_index("ix_product_deletion_audits_product_id", "product_deletion_audits", ["product_id"])
    op.create_index("ix_product_deletion_audits_event_type", "product_deletion_audits", ["event_type"])
    op.create_index("ix_product_deletion_audits_request_id", "product_deletion_audits", ["request_id"])
    op.create_index("ix_product_deletion_audits_created_at", "product_deletion_audits", ["created_at"])


def downgrade() -> None:
    for index in (
        "ix_product_deletion_audits_created_at",
        "ix_product_deletion_audits_request_id",
        "ix_product_deletion_audits_event_type",
        "ix_product_deletion_audits_product_id",
        "ix_product_deletion_audits_store_id",
    ):
        op.drop_index(index, table_name="product_deletion_audits")
    op.drop_table("product_deletion_audits")
    op.drop_column("stores", "allow_test_data_purge")
    op.drop_index("ix_products_is_test_data", table_name="products")
    op.drop_column("products", "is_test_data")

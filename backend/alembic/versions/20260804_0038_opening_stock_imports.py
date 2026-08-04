"""Add strict audited opening-stock import lifecycle tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260804_0038"
down_revision = "20260803_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opening_stock_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reversed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100)), sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False), sa.Column("idempotency_key", sa.String(120)),
        sa.Column("backup_evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("valid_row_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_quantity", sa.Integer(), nullable=False, server_default="0"), sa.Column("total_cost_value", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("total_retail_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("posted_at", sa.DateTime(timezone=True)), sa.Column("reversed_at", sa.DateTime(timezone=True)), sa.Column("reversal_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "file_sha256", name="uq_opening_stock_import_file"),
    )
    op.create_index("ix_opening_stock_imports_store_id", "opening_stock_imports", ["store_id"])
    op.create_index("ix_opening_stock_imports_status", "opening_stock_imports", ["status"])
    op.create_index("ix_opening_stock_imports_idempotency_key", "opening_stock_imports", ["idempotency_key"])
    op.create_table(
        "opening_stock_import_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("opening_stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opening_stock_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False), sa.Column("normalized_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("validation_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL")), sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL")), sa.Column("cost_lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_cost_lots.id", ondelete="SET NULL")), sa.Column("stock_history_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_history.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("opening_stock_import_id", "row_number", name="uq_opening_stock_import_row"),
    )
    op.create_index("ix_opening_stock_import_rows_opening_stock_import_id", "opening_stock_import_rows", ["opening_stock_import_id"])
    op.create_table(
        "opening_stock_import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False), sa.Column("opening_stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opening_stock_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("opening_stock_import_row_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opening_stock_import_rows.id", ondelete="CASCADE")), sa.Column("row_number", sa.Integer()), sa.Column("field", sa.String(80)), sa.Column("code", sa.String(80), nullable=False), sa.Column("message", sa.String(500), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_opening_stock_import_errors_opening_stock_import_id", "opening_stock_import_errors", ["opening_stock_import_id"])
    op.create_index("ix_opening_stock_import_errors_opening_stock_import_row_id", "opening_stock_import_errors", ["opening_stock_import_row_id"])
    op.create_table(
        "opening_stock_import_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False), sa.Column("opening_stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opening_stock_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("action", sa.String(40), nullable=False), sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("request_id", sa.String(120)), sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_opening_stock_import_audits_opening_stock_import_id", "opening_stock_import_audits", ["opening_stock_import_id"])


def downgrade() -> None:
    op.drop_table("opening_stock_import_audits")
    op.drop_table("opening_stock_import_errors")
    op.drop_table("opening_stock_import_rows")
    op.drop_table("opening_stock_imports")

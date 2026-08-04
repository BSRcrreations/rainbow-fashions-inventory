from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260803_0039"
down_revision = "20260803_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("stock_imports", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False), sa.Column("import_type", sa.String(40), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("source_filename", sa.String(255), nullable=False), sa.Column("file_sha256", sa.String(64), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("confirmed_at", sa.DateTime(timezone=True)), sa.Column("request_id", sa.String(120), nullable=False), sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("failure_details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("store_id", "idempotency_key", name="uq_stock_import_store_idempotency"))
    op.create_table("stock_import_rows", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("row_number", sa.Integer(), nullable=False), sa.Column("sku", sa.String(80)), sa.Column("barcode", sa.String(80)), sa.Column("quantity", sa.Integer()), sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT")), sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="RESTRICT")), sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")), sa.Column("normalized_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("opening_stock_movement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_history.id", ondelete="SET NULL"), unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("stock_import_id", "row_number", name="uq_stock_import_row_number"))
    op.create_table("stock_import_backups", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_imports.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("status", sa.String(40), nullable=False), sa.Column("backup_path", sa.String(1000)), sa.Column("sha256", sa.String(64)), sa.Column("size_bytes", sa.Integer()), sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("error_code", sa.String(80)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("stock_import_rollbacks", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("stock_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_imports.id", ondelete="RESTRICT"), nullable=False, unique=True), sa.Column("status", sa.String(40), nullable=False), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("completed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("conflict_report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("request_id", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(timezone=True)))
    for table, columns in (("stock_imports", ("store_id", "status", "file_sha256")), ("stock_import_rows", ("stock_import_id", "product_id", "product_variant_id")), ("stock_import_backups", ("stock_import_id",)), ("stock_import_rollbacks", ("stock_import_id", "status"))):
        for column in columns: op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("stock_import_rollbacks")
    op.drop_table("stock_import_backups")
    op.drop_table("stock_import_rows")
    op.drop_table("stock_imports")

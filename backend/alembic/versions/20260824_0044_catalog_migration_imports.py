"""Add idempotent TEST-to-production catalog migration evidence.

Revision ID: 20260824_0044
Revises: 20260815_0043
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260824_0044"
down_revision = "20260815_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "catalog_migration_imports",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("package_id", sa.String(80), nullable=False),
        sa.Column("package_sha256", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source_database", sa.String(120), nullable=False),
        sa.Column("source_git_sha", sa.String(64), nullable=False),
        sa.Column("executed_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("manifest_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("failure_details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "package_id", name="uq_catalog_migration_import_store_package"),
    )
    op.create_index("ix_catalog_migration_imports_store_id", "catalog_migration_imports", ["store_id"])
    op.create_index("ix_catalog_migration_imports_status", "catalog_migration_imports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_catalog_migration_imports_status", table_name="catalog_migration_imports")
    op.drop_index("ix_catalog_migration_imports_store_id", table_name="catalog_migration_imports")
    op.drop_table("catalog_migration_imports")

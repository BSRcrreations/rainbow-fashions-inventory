"""add backup job history

Revision ID: 20260803_0036
Revises: 20260802_0035
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260803_0036"
down_revision = "20260802_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("local_file_path", sa.String(length=512)),
        sa.Column("remote_file_path", sa.String(length=512)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("checksum", sa.String(length=64)),
        sa.Column("retention_until", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backup_jobs_job_type", "backup_jobs", ["job_type"])
    op.create_index("ix_backup_jobs_status", "backup_jobs", ["status"])
    op.create_index("ix_backup_jobs_requested_by", "backup_jobs", ["requested_by"])


def downgrade() -> None:
    op.drop_index("ix_backup_jobs_requested_by", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_status", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_job_type", table_name="backup_jobs")
    op.drop_table("backup_jobs")

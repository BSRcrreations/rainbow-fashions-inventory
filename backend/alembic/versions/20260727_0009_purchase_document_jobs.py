"""add async purchase document jobs

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None

def upgrade() -> None:
    job_status = postgresql.ENUM("UPLOADED", "QUEUED", "PREPROCESSING", "OCR_RUNNING", "AI_EXTRACTION", "PRODUCT_MATCHING", "VALIDATING", "REVIEW_REQUIRED", "COMPLETED", "FAILED", name="document_job_status", create_type=False)
    job_status.create(op.get_bind(), checkfirst=True)
    op.create_table("purchase_documents", sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False), sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("created_by", postgresql.UUID(as_uuid=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["uploaded_file_id"], ["uploaded_files.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_purchase_documents_store_id", "purchase_documents", ["store_id"])
    op.create_index("ix_purchase_documents_sha256", "purchase_documents", ["sha256"])
    op.create_table("document_processing_jobs", sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False), sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", job_status, server_default="QUEUED", nullable=False), sa.Column("progress", sa.Integer(), server_default="0", nullable=False), sa.Column("message", sa.String(240), server_default="Queued for invoice recognition", nullable=False), sa.Column("request_id", sa.String(36), nullable=False), sa.Column("provider", sa.String(40), server_default="mock", nullable=False), sa.Column("result", postgresql.JSONB()), sa.Column("error_code", sa.String(80)), sa.Column("error_message", sa.String(300)), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["document_id"], ["purchase_documents.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    for column in ("document_id", "store_id", "request_id"):
        op.create_index(f"ix_document_processing_jobs_{column}", "document_processing_jobs", [column])

def downgrade() -> None:
    for column in ("request_id", "store_id", "document_id"):
        op.drop_index(f"ix_document_processing_jobs_{column}", table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")
    op.drop_index("ix_purchase_documents_sha256", table_name="purchase_documents")
    op.drop_index("ix_purchase_documents_store_id", table_name="purchase_documents")
    op.drop_table("purchase_documents")
    postgresql.ENUM(name="document_job_status").drop(op.get_bind(), checkfirst=True)

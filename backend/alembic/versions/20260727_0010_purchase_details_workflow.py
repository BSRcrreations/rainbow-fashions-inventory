"""add purchase details workflow fields and audit history

Revision ID: 20260727_0010
Revises: 20260727_0009
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("purchase_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_documents.id", ondelete="SET NULL")))
    op.add_column("purchases", sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_processing_jobs.id", ondelete="SET NULL")))
    op.add_column("purchases", sa.Column("due_date", sa.Date()))
    op.add_column("purchases", sa.Column("payment_mode", sa.String(40), server_default="CREDIT", nullable=False))
    op.add_column("purchases", sa.Column("amount_paid", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("place_of_supply", sa.String(120)))
    op.add_column("purchases", sa.Column("purchase_reference", sa.String(120)))
    op.add_column("purchases", sa.Column("notes", sa.String(1000)))
    op.add_column("purchases", sa.Column("warehouse", sa.String(120)))
    op.add_column("purchases", sa.Column("currency", sa.String(3), server_default="INR", nullable=False))
    op.add_column("purchases", sa.Column("packaging_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("freight_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("round_off", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_index("ix_purchases_due_date", "purchases", ["due_date"])
    op.create_unique_constraint("uq_purchases_purchase_document_id", "purchases", ["purchase_document_id"])

    op.add_column("purchase_items", sa.Column("hsn_sac", sa.String(40)))
    op.add_column("purchase_items", sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0", nullable=False))

    op.create_table(
        "purchase_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("before_data", postgresql.JSONB()),
        sa.Column("after_data", postgresql.JSONB()),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchase_audits_purchase_id", "purchase_audits", ["purchase_id"])

    # Remove only known pre-production OCR placeholder drafts; confirmed records remain intact.
    op.execute("DELETE FROM purchases WHERE supplier_name = 'ARK Distributors' AND status IN ('DRAFT', 'REVIEWED')")
    op.execute("DELETE FROM suppliers WHERE name = 'ARK Distributors' AND NOT EXISTS (SELECT 1 FROM purchases WHERE purchases.supplier_id = suppliers.id)")


def downgrade() -> None:
    op.drop_index("ix_purchase_audits_purchase_id", table_name="purchase_audits")
    op.drop_table("purchase_audits")
    op.drop_column("purchase_items", "tax_rate")
    op.drop_column("purchase_items", "hsn_sac")
    op.drop_constraint("uq_purchases_purchase_document_id", "purchases", type_="unique")
    op.drop_index("ix_purchases_due_date", table_name="purchases")
    for column in ("version", "round_off", "freight_amount", "packaging_amount", "currency", "warehouse", "notes", "purchase_reference", "place_of_supply", "amount_paid", "payment_mode", "due_date", "processing_job_id", "purchase_document_id"):
        op.drop_column("purchases", column)

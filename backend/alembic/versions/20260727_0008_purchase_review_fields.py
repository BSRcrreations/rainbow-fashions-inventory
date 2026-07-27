"""add purchase dates and review metadata

Revision ID: 20260727_0008
Revises: 20260724_0007
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0008"
down_revision = "20260724_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("purchase_date", sa.Date(), nullable=True))
    op.execute("UPDATE purchases SET purchase_date = COALESCE(invoice_date, created_at::date, CURRENT_DATE) WHERE purchase_date IS NULL")
    op.alter_column("purchases", "purchase_date", nullable=False)
    op.add_column("purchases", sa.Column("received_date", sa.Date()))
    op.add_column("purchases", sa.Column("subtotal", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("image_hash", sa.String(64)))
    op.add_column("purchases", sa.Column("ai_processing_status", sa.String(40), server_default="DRAFT", nullable=False))
    op.create_index("ix_purchases_purchase_date", "purchases", ["purchase_date"])
    op.create_index("ix_purchases_received_date", "purchases", ["received_date"])
    op.create_index("ix_purchases_image_hash", "purchases", ["image_hash"])

    op.add_column("purchase_items", sa.Column("barcode", sa.String(80)))
    op.add_column("purchase_items", sa.Column("supplier_product_code", sa.String(120)))
    op.add_column("purchase_items", sa.Column("unit", sa.String(40), server_default="Each", nullable=False))
    op.add_column("purchase_items", sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("match_status", sa.String(40), server_default="NOT_FOUND", nullable=False))
    op.add_column("purchase_items", sa.Column("batch_number", sa.String(120)))
    op.add_column("purchase_items", sa.Column("expiry_date", sa.Date()))
    op.add_column("purchase_items", sa.Column("user_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_purchase_items_barcode", "purchase_items", ["barcode"])


def downgrade() -> None:
    op.drop_index("ix_purchase_items_barcode", table_name="purchase_items")
    for column in ("user_verified", "expiry_date", "batch_number", "match_status", "tax_amount", "discount", "unit", "supplier_product_code", "barcode"):
        op.drop_column("purchase_items", column)
    op.drop_index("ix_purchases_image_hash", table_name="purchases")
    op.drop_index("ix_purchases_received_date", table_name="purchases")
    op.drop_index("ix_purchases_purchase_date", table_name="purchases")
    for column in ("ai_processing_status", "image_hash", "tax_amount", "discount", "subtotal", "received_date", "purchase_date"):
        op.drop_column("purchases", column)

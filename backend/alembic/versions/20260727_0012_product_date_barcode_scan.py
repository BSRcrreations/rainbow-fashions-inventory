"""add product date for barcode labels and POS scanning

Revision ID: 20260727_0012
Revises: 20260727_0011
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0012"
down_revision = "20260727_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable first so historical products keep their original records intact.
    op.add_column("products", sa.Column("product_date", sa.Date(), nullable=True))
    op.execute("UPDATE products SET product_date = COALESCE(created_at::date, CURRENT_DATE) WHERE product_date IS NULL")
    op.alter_column("products", "product_date", nullable=False, server_default=sa.text("CURRENT_DATE"))


def downgrade() -> None:
    op.drop_column("products", "product_date")

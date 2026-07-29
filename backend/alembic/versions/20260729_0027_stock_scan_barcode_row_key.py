"""key scan review rows by their barcode

Revision ID: 20260729_0027
Revises: 20260729_0026
Create Date: 2026-07-28
"""

from alembic import op


revision = "20260729_0027"
down_revision = "20260729_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", ["session_id", "barcode"])


def downgrade() -> None:
    op.drop_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", ["session_id", "product_barcode_id"])

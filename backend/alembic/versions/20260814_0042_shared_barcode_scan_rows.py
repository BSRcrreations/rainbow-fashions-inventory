"""allow one scan session to stage shared-barcode sizes separately

Revision ID: 20260814_0042
Revises: 20260814_0041
Create Date: 2026-08-14
"""

from alembic import op


revision = "20260814_0042"
down_revision = "20260814_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint(
        "uq_stock_scan_session_barcode_variant",
        "stock_scan_session_items",
        ["session_id", "barcode", "product_variant_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_stock_scan_session_barcode_variant", "stock_scan_session_items", type_="unique")
    op.create_unique_constraint("uq_stock_scan_session_barcode", "stock_scan_session_items", ["session_id", "barcode"])

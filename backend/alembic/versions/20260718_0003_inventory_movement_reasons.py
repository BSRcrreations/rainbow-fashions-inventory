"""add explicit inventory movement reasons

Revision ID: 20260718_0003
Revises: 20260718_0002
Create Date: 2026-07-18
"""

from alembic import op


revision = "20260718_0003"
down_revision = "20260718_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'CUSTOMER_RETURN'")
        op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'SUPPLIER_RETURN'")
        op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'DAMAGE'")
        op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'MANUAL_ADJUSTMENT'")
    op.execute("UPDATE stock_history SET movement_type = 'MANUAL_ADJUSTMENT' WHERE movement_type = 'ADJUSTMENT'")


def downgrade() -> None:
    op.execute("UPDATE stock_history SET movement_type = 'ADJUSTMENT' WHERE movement_type = 'MANUAL_ADJUSTMENT'")

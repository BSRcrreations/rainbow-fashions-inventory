"""add sale correction movement values

Revision ID: 20260724_0007
Revises: 20260724_0006
Create Date: 2026-07-24
"""

from alembic import op


revision = "20260724_0007"
down_revision = "20260724_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'SALE_EDIT_RETURN'")
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'SALE_EDIT_DECREASE'")
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'SALE_VOID'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without rewriting dependent columns.
    pass

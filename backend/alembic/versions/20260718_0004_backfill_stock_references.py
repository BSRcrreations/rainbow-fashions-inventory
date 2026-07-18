"""backfill references for legacy stock movements

Revision ID: 20260718_0004
Revises: 20260718_0003
Create Date: 2026-07-18
"""

from alembic import op


revision = "20260718_0004"
down_revision = "20260718_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE stock_history
        SET reference = 'LEGACY-' || movement_type::text || '-' || upper(substr(id::text, 1, 8))
        WHERE reference IS NULL OR btrim(reference) = ''
        """
    )


def downgrade() -> None:
    pass

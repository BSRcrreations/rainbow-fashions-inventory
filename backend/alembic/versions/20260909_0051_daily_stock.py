"""Separate daily positive stock entries from opening inventory and corrections."""
from alembic import op

revision = "20260909_0051"
down_revision = "20260909_0050"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE stock_scan_mode ADD VALUE IF NOT EXISTS 'DAILY_STOCK'")


def downgrade():
    # PostgreSQL enum labels cannot be safely removed while referenced by drafts.
    pass

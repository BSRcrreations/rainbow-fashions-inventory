"""Repair the missing VOIDED label on production purchase_status.

Revision ID: 20260901_0047
Revises: 20260825_0046
Create Date: 2026-09-01

Some production databases were recorded at revision 0046 while the historical
0017 enum alteration had not been applied.  This is intentionally additive and
safe to run on correctly migrated databases.
"""

from alembic import op


revision = "20260901_0047"
down_revision = "20260825_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE purchase_status ADD VALUE IF NOT EXISTS 'VOIDED'")


def downgrade() -> None:
    # PostgreSQL does not safely support removing enum labels in place.
    pass

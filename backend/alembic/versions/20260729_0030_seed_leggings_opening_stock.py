"""Retired historical stock seed; opening stock requires an operator-confirmed import.

Previously applied stock history is retained. New installs and upgrades must never
create business stock implicitly as a side effect of a schema migration.
"""
revision = "20260729_0030"
down_revision = "20260717_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""store explicit checkout discount type and value

Revision ID: 20260802_0034
Revises: 20260802_0033
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op


revision = "20260802_0034"
down_revision = "20260802_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing sales used the `discount` amount exclusively. Preserve that
    # history as a fixed-amount discount before defaulting new checkout sales
    # to percentage mode.
    op.add_column("sales", sa.Column("discount_type", sa.String(length=20), server_default="FIXED_AMOUNT", nullable=False))
    op.add_column("sales", sa.Column("discount_value", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("sales", sa.Column("discount_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.execute("UPDATE sales SET discount_value = discount, discount_amount = discount, discount_type = 'FIXED_AMOUNT'")
    op.alter_column("sales", "discount_type", server_default="PERCENTAGE")


def downgrade() -> None:
    op.drop_column("sales", "discount_amount")
    op.drop_column("sales", "discount_value")
    op.drop_column("sales", "discount_type")

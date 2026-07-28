"""add invoice-level purchase tax rate

Revision ID: 20260728_0019
Revises: 20260728_0018
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op


revision = "20260728_0019"
down_revision = "20260728_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchases",
        sa.Column(
            "invoice_tax_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column("purchases", "invoice_tax_rate", server_default=None)


def downgrade() -> None:
    op.drop_column("purchases", "invoice_tax_rate")

"""Add GST rate and HSN code to products

Revision ID: 20260717_0002
Revises: 20260716_0001
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260717_0002"
down_revision: Union[str, None] = "20260716_0001"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("gst_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column("products", sa.Column("hsn_code", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "hsn_code")
    op.drop_column("products", "gst_rate")

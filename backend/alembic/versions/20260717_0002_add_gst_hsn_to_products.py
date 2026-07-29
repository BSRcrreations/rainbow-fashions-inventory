"""Add GST rate and HSN code to products

Revision ID: 20260717_0002
Revises: 20260729_0029
Create Date: 2026-07-29 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260717_0002"
down_revision = "20260729_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS gst_rate NUMERIC(5, 2),
            ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(20);
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS hsn_code")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS gst_rate")

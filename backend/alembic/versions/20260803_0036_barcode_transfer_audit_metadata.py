"""add barcode transfer audit metadata

Revision ID: 20260803_0036
Revises: 20260802_0035
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260803_0036"
down_revision = "20260802_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_barcode_audits",
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.alter_column("product_barcode_audits", "metadata_json", server_default=None)


def downgrade() -> None:
    op.drop_column("product_barcode_audits", "metadata_json")

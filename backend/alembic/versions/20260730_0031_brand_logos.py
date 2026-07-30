"""add logo storage to brands

Revision ID: 20260730_0031
Revises: 20260729_0030
Create Date: 2026-07-30
"""

from alembic import op


revision = "20260730_0031"
down_revision = "20260729_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE brands ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)")


def downgrade() -> None:
    op.execute("ALTER TABLE brands DROP COLUMN IF EXISTS logo_url")

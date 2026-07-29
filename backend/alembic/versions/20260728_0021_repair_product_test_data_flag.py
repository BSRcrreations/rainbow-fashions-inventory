"""repair product test-data flag for stamped legacy schemas

Revision ID: 20260728_0021
Revises: 20260728_0020
Create Date: 2026-07-28
"""

from alembic import op


revision = "20260728_0021"
down_revision = "20260728_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_test_data BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_is_test_data ON products (is_test_data)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_is_test_data")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS is_test_data")

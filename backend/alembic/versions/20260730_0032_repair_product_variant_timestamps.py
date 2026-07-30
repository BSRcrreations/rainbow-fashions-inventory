"""repair product variant timestamps

Revision ID: 20260730_0032
Revises: 20260730_0031
Create Date: 2026-07-30
"""

from alembic import op


revision = "20260730_0032"
down_revision = "20260730_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older variants were created before `updated_at` received a database
    # default. Backfill them before making the API's required datetime field
    # enforceable at the database level.
    op.execute("ALTER TABLE product_variants ALTER COLUMN updated_at SET DEFAULT now()")
    op.execute("UPDATE product_variants SET updated_at = COALESCE(created_at, now()) WHERE updated_at IS NULL")
    op.execute("ALTER TABLE product_variants ALTER COLUMN updated_at SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE product_variants ALTER COLUMN updated_at DROP NOT NULL")
    op.execute("ALTER TABLE product_variants ALTER COLUMN updated_at DROP DEFAULT")

"""add product sku and image url

Revision ID: 20260716_0001
Revises:
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("sku", sa.String(length=80), nullable=True))
    op.add_column("products", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_unique_constraint("uq_products_sku", "products", ["sku"])


def downgrade() -> None:
    op.drop_constraint("uq_products_sku", "products", type_="unique")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_column("products", "image_url")
    op.drop_column("products", "sku")

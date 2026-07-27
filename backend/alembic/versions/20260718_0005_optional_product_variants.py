"""add optional product color and size variants

Revision ID: 20260718_0005
Revises: 20260718_0004
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_0005"
down_revision = "20260718_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("color", sa.String(80), nullable=True),
        sa.Column("size", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "color", "size", name="uq_product_variants_combination"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.execute(
        """
        INSERT INTO product_variants (product_id, color, size)
        SELECT id, NULLIF(trim(color), ''), NULLIF(trim(size), '')
        FROM products
        WHERE NULLIF(trim(color), '') IS NOT NULL OR NULLIF(trim(size), '') IS NOT NULL
        """
    )
    op.drop_constraint("uq_products_variant", "products", type_="unique")
    op.alter_column("products", "color", existing_type=sa.String(80), nullable=True)
    op.alter_column("products", "size", existing_type=sa.String(60), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE products SET color = COALESCE(color, 'Standard'), size = COALESCE(size, 'Standard')")
    op.alter_column("products", "size", existing_type=sa.String(60), nullable=False)
    op.alter_column("products", "color", existing_type=sa.String(80), nullable=False)
    op.create_unique_constraint(
        "uq_products_variant",
        "products",
        ["category_id", "subcategory_id", "brand_id", "name", "size", "color"],
    )
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")

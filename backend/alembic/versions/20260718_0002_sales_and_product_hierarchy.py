"""add sales and category-owned product hierarchy

Revision ID: 20260718_0002
Revises: 20260716_0001
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_0002"
down_revision = "20260716_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subcategories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "name", name="uq_subcategories_category_name"),
        sa.UniqueConstraint("id", "category_id", name="uq_subcategories_id_category"),
    )
    op.create_index("ix_subcategories_category_id", "subcategories", ["category_id"])
    op.create_index("ix_subcategories_name", "subcategories", ["name"])

    op.add_column("brands", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_constraint("uq_brands_name", "brands", type_="unique")
    op.execute(
        """
        UPDATE brands b
        SET category_id = (
            SELECT p.category_id FROM products p
            WHERE p.brand_id = b.id
            ORDER BY p.category_id::text
            LIMIT 1
        )
        """
    )
    op.execute(
        """
        INSERT INTO categories (id, name, description, is_active)
        SELECT gen_random_uuid(), 'Uncategorized', 'Migrated catalog records', TRUE
        WHERE EXISTS (SELECT 1 FROM brands WHERE category_id IS NULL)
          AND NOT EXISTS (SELECT 1 FROM categories)
        """
    )
    op.execute(
        """
        UPDATE brands
        SET category_id = (SELECT id FROM categories ORDER BY created_at, id LIMIT 1)
        WHERE category_id IS NULL
        """
    )
    op.create_foreign_key("fk_brands_category_id", "brands", "categories", ["category_id"], ["id"], ondelete="CASCADE")
    op.alter_column("brands", "category_id", nullable=False)
    op.create_unique_constraint("uq_brands_category_name", "brands", ["category_id", "name"])
    op.create_unique_constraint("uq_brands_id_category", "brands", ["id", "category_id"])
    op.create_index("ix_brands_category_id", "brands", ["category_id"])

    op.execute(
        """
        DO $$
        DECLARE
            relation RECORD;
            replacement_id UUID;
        BEGIN
            FOR relation IN
                SELECT b.id AS brand_id, b.name, b.description, b.is_active, p.category_id
                FROM brands b
                JOIN products p ON p.brand_id = b.id
                WHERE p.category_id <> b.category_id
                GROUP BY b.id, b.name, b.description, b.is_active, p.category_id
            LOOP
                INSERT INTO brands (id, category_id, name, description, is_active)
                VALUES (gen_random_uuid(), relation.category_id, relation.name, relation.description, relation.is_active)
                ON CONFLICT (category_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id INTO replacement_id;

                UPDATE products
                SET brand_id = replacement_id
                WHERE brand_id = relation.brand_id AND category_id = relation.category_id;
            END LOOP;
        END $$
        """
    )

    op.execute(
        """
        INSERT INTO subcategories (category_id, name, description, is_active)
        SELECT id, 'General', 'Migrated products', TRUE FROM categories
        ON CONFLICT (category_id, name) DO NOTHING
        """
    )
    op.add_column("products", sa.Column("subcategory_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE products p
        SET subcategory_id = s.id
        FROM subcategories s
        WHERE s.category_id = p.category_id AND s.name = 'General'
        """
    )
    op.alter_column("products", "subcategory_id", nullable=False)
    op.create_foreign_key("fk_products_subcategory_id", "products", "subcategories", ["subcategory_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key(
        "fk_products_subcategory_category",
        "products",
        "subcategories",
        ["subcategory_id", "category_id"],
        ["id", "category_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_products_brand_category",
        "products",
        "brands",
        ["brand_id", "category_id"],
        ["id", "category_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_products_subcategory_id", "products", ["subcategory_id"])
    op.drop_constraint("uq_products_variant", "products", type_="unique")
    op.create_unique_constraint(
        "uq_products_variant",
        "products",
        ["category_id", "subcategory_id", "brand_id", "name", "size", "color"],
    )

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True)),
        sa.Column("invoice_number", sa.String(120), nullable=False),
        sa.Column("customer_name", sa.String(180)),
        sa.Column("payment_mode", sa.String(40), nullable=False),
        sa.Column("cashier_id", postgresql.UUID(as_uuid=True)),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("profit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("sale_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("subtotal >= 0 AND discount >= 0 AND total_amount >= 0 AND cost_amount >= 0", name="ck_sales_amounts_non_negative"),
        sa.CheckConstraint("discount <= subtotal", name="ck_sales_discount_not_above_subtotal"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number", name="uq_sales_invoice_number"),
    )
    for column in ("store_id", "invoice_number", "customer_name", "payment_mode", "cashier_id", "sale_date"):
        op.create_index(f"ix_sales_{column}", "sales", [column])

    op.create_table(
        "sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0 AND unit_cost >= 0 AND line_total >= 0", name="ck_sale_items_amounts_non_negative"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])

    op.add_column("stock_history", sa.Column("sale_id", postgresql.UUID(as_uuid=True)))
    op.add_column("stock_history", sa.Column("sale_item_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_stock_history_sale_id", "stock_history", "sales", ["sale_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_stock_history_sale_item_id", "stock_history", "sale_items", ["sale_item_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_stock_history_sale_id", "stock_history", ["sale_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_history_sale_id", table_name="stock_history")
    op.drop_constraint("fk_stock_history_sale_item_id", "stock_history", type_="foreignkey")
    op.drop_constraint("fk_stock_history_sale_id", "stock_history", type_="foreignkey")
    op.drop_column("stock_history", "sale_item_id")
    op.drop_column("stock_history", "sale_id")
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.drop_constraint("uq_products_variant", "products", type_="unique")
    op.create_unique_constraint("uq_products_variant", "products", ["category_id", "brand_id", "name", "size", "color"])
    op.drop_constraint("fk_products_brand_category", "products", type_="foreignkey")
    op.drop_constraint("fk_products_subcategory_category", "products", type_="foreignkey")
    op.drop_constraint("fk_products_subcategory_id", "products", type_="foreignkey")
    op.drop_index("ix_products_subcategory_id", table_name="products")
    op.drop_column("products", "subcategory_id")
    op.execute(
        """
        DO $$
        DECLARE duplicate RECORD; keeper UUID;
        BEGIN
            FOR duplicate IN SELECT name FROM brands GROUP BY name HAVING count(*) > 1 LOOP
                SELECT id INTO keeper FROM brands WHERE name = duplicate.name ORDER BY created_at, id LIMIT 1;
                UPDATE products SET brand_id = keeper WHERE brand_id IN (SELECT id FROM brands WHERE name = duplicate.name AND id <> keeper);
                DELETE FROM brands WHERE name = duplicate.name AND id <> keeper;
            END LOOP;
        END $$
        """
    )
    op.drop_index("ix_brands_category_id", table_name="brands")
    op.drop_constraint("uq_brands_id_category", "brands", type_="unique")
    op.drop_constraint("uq_brands_category_name", "brands", type_="unique")
    op.drop_constraint("fk_brands_category_id", "brands", type_="foreignkey")
    op.drop_column("brands", "category_id")
    op.create_unique_constraint("uq_brands_name", "brands", ["name"])
    op.drop_table("subcategories")

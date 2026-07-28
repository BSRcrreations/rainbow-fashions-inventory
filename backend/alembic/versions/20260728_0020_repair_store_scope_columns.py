"""repair store scope columns for stamped legacy schemas

Revision ID: 20260728_0020
Revises: 20260728_0019
Create Date: 2026-07-28
"""

from alembic import op


revision = "20260728_0020"
down_revision = "20260728_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS store_id UUID")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_store_id ON products (store_id)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_products_store_id') THEN
                ALTER TABLE products ADD CONSTRAINT fk_products_store_id
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE products AS product
        SET store_id = scoped.store_id
        FROM (
            SELECT product_id, MIN(store_id::text)::uuid AS store_id
            FROM product_inventory
            GROUP BY product_id
            HAVING COUNT(DISTINCT store_id) = 1
        ) AS scoped
        WHERE product.id = scoped.product_id AND product.store_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE products AS product
        SET store_id = scoped.store_id
        FROM (
            SELECT product_id, MIN(store_id::text)::uuid AS store_id
            FROM stock_history
            WHERE store_id IS NOT NULL
            GROUP BY product_id
            HAVING COUNT(DISTINCT store_id) = 1
        ) AS scoped
        WHERE product.id = scoped.product_id AND product.store_id IS NULL
        """
    )

    for table_name in ("categories", "brands", "subcategories"):
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS store_id UUID")

    op.execute(
        """
        DO $$
        DECLARE fallback_store UUID;
        BEGIN
            SELECT id INTO fallback_store FROM stores ORDER BY created_at, id LIMIT 1;
            IF fallback_store IS NULL AND EXISTS (
                SELECT 1 FROM categories WHERE store_id IS NULL
                UNION ALL SELECT 1 FROM brands WHERE store_id IS NULL
                UNION ALL SELECT 1 FROM subcategories WHERE store_id IS NULL
            ) THEN
                RAISE EXCEPTION 'Cannot scope catalog data because no store exists';
            END IF;
            UPDATE categories SET store_id = fallback_store WHERE store_id IS NULL;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE brands AS brand
        SET store_id = category.store_id
        FROM categories AS category
        WHERE brand.category_id = category.id AND brand.store_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE subcategories AS subcategory
        SET store_id = category.store_id
        FROM categories AS category
        WHERE subcategory.category_id = category.id AND subcategory.store_id IS NULL
        """
    )
    for table_name in ("categories", "brands", "subcategories"):
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN store_id SET NOT NULL")

    _replace_unique("categories", "UNIQUE (name)", "uq_categories_store_name", "UNIQUE (store_id, name)")
    _replace_unique("brands", "UNIQUE (category_id, name)", "uq_brands_store_category_name", "UNIQUE (store_id, category_id, name)")
    _replace_unique("subcategories", "UNIQUE (category_id, name)", "uq_subcategories_store_category_name", "UNIQUE (store_id, category_id, name)")

    for table_name in ("categories", "brands", "subcategories"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_{table_name}_store_id') THEN
                    ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_store_id
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
                END IF;
            END $$;
            """
        )
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_store_id ON {table_name} (store_id)")


def downgrade() -> None:
    for table_name, constraint_name in (
        ("subcategories", "uq_subcategories_store_category_name"),
        ("brands", "uq_brands_store_category_name"),
        ("categories", "uq_categories_store_name"),
    ):
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS fk_{table_name}_store_id")
        op.execute(f"DROP INDEX IF EXISTS ix_{table_name}_store_id")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS fk_products_store_id")
    op.execute("DROP INDEX IF EXISTS ix_products_store_id")


def _replace_unique(table_name: str, old_definition: str, new_name: str, new_definition: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE constraint_name TEXT;
        BEGIN
            FOR constraint_name IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = '{table_name}'::regclass
                  AND contype = 'u'
                  AND pg_get_constraintdef(oid) = '{old_definition}'
            LOOP
                EXECUTE format('ALTER TABLE {table_name} DROP CONSTRAINT %I', constraint_name);
            END LOOP;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{new_name}') THEN
                ALTER TABLE {table_name} ADD CONSTRAINT {new_name} {new_definition};
            END IF;
        END $$;
        """
    )

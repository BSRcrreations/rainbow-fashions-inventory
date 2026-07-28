"""reconcile store-scoped catalog schema

Revision ID: 20260728_0018
Revises: 20260728_0017
Create Date: 2026-07-28
"""

from alembic import op


revision = "20260728_0018"
down_revision = "20260728_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("categories", "brands", "subcategories"):
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS store_id UUID")

    op.execute(
        """
        DO $$
        DECLARE fallback_store UUID;
        BEGIN
            SELECT id INTO fallback_store FROM stores ORDER BY created_at, id LIMIT 1;
            IF fallback_store IS NULL AND EXISTS (SELECT 1 FROM categories WHERE store_id IS NULL) THEN
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

    op.execute(
        """
        DO $$
        DECLARE constraint_name TEXT;
        BEGIN
            FOR constraint_name IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'categories'::regclass
                  AND contype = 'u'
                  AND pg_get_constraintdef(oid) = 'UNIQUE (name)'
            LOOP
                EXECUTE format('ALTER TABLE categories DROP CONSTRAINT %I', constraint_name);
            END LOOP;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_categories_store_name') THEN
                ALTER TABLE categories ADD CONSTRAINT uq_categories_store_name UNIQUE (store_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_categories_store_id') THEN
                ALTER TABLE categories ADD CONSTRAINT fk_categories_store_id FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE constraint_name TEXT;
        BEGIN
            FOR constraint_name IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'brands'::regclass
                  AND contype = 'u'
                  AND pg_get_constraintdef(oid) = 'UNIQUE (category_id, name)'
            LOOP
                EXECUTE format('ALTER TABLE brands DROP CONSTRAINT %I', constraint_name);
            END LOOP;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_brands_store_category_name') THEN
                ALTER TABLE brands ADD CONSTRAINT uq_brands_store_category_name UNIQUE (store_id, category_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_brands_store_id') THEN
                ALTER TABLE brands ADD CONSTRAINT fk_brands_store_id FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE constraint_name TEXT;
        BEGIN
            FOR constraint_name IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'subcategories'::regclass
                  AND contype = 'u'
                  AND pg_get_constraintdef(oid) = 'UNIQUE (category_id, name)'
            LOOP
                EXECUTE format('ALTER TABLE subcategories DROP CONSTRAINT %I', constraint_name);
            END LOOP;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_subcategories_store_category_name') THEN
                ALTER TABLE subcategories ADD CONSTRAINT uq_subcategories_store_category_name UNIQUE (store_id, category_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_subcategories_store_id') THEN
                ALTER TABLE subcategories ADD CONSTRAINT fk_subcategories_store_id FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    for table_name in ("categories", "brands", "subcategories"):
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
        op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS store_id")

"""seed validated leggings opening stock for Rainbow Fashions

Revision ID: 20260729_0030
Revises: 20260717_0002
Create Date: 2026-07-29
"""

from alembic import op


revision = "20260729_0030"
down_revision = "20260717_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the owner-approved opening balance once, without affecting other stores."""
    op.execute(
        """
        DO $$
        DECLARE
            shop_store_id uuid;
            owner_id uuid;
            leggings_category_id uuid;
            general_subcategory_id uuid;
            prisma_brand_id uuid;
            fly_birds_brand_id uuid;
            prisma_product_id uuid;
            fly_birds_product_id uuid;
            line record;
            variant_id uuid;
            target_product_id uuid;
            product_stock_before integer;
            variant_stock_before integer;
            opening_reference constant varchar(180) := 'Opening stock – Leggings 2026-07-29';
        BEGIN
            SELECT id INTO shop_store_id
            FROM stores
            WHERE lower(name) = 'rainbow fashions'
            ORDER BY created_at, id
            LIMIT 1;
            IF shop_store_id IS NULL THEN
                RAISE NOTICE 'Rainbow Fashions store was not found; leggings opening stock was not seeded.';
                RETURN;
            END IF;

            SELECT id INTO owner_id
            FROM users
            WHERE store_id = shop_store_id AND role = 'OWNER' AND is_active
            ORDER BY created_at, id
            LIMIT 1;
            IF owner_id IS NULL THEN
                RAISE EXCEPTION 'An active owner is required to seed opening stock for Rainbow Fashions';
            END IF;

            -- Correct the legacy spelling only if the correctly named category does not already exist.
            IF NOT EXISTS (SELECT 1 FROM categories WHERE store_id = shop_store_id AND lower(name) = 'leggings') THEN
                UPDATE categories SET name = 'Leggings'
                WHERE store_id = shop_store_id AND lower(name) = 'leggins';
            END IF;
            INSERT INTO categories (store_id, name, description, is_active)
            SELECT shop_store_id, 'Leggings', 'Leggings inventory', true
            WHERE NOT EXISTS (SELECT 1 FROM categories WHERE store_id = shop_store_id AND lower(name) = 'leggings');
            SELECT id INTO leggings_category_id
            FROM categories WHERE store_id = shop_store_id AND lower(name) = 'leggings' LIMIT 1;

            INSERT INTO subcategories (store_id, category_id, name, description, is_active)
            SELECT shop_store_id, leggings_category_id, 'General', 'General leggings', true
            WHERE NOT EXISTS (
                SELECT 1 FROM subcategories
                WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'general'
            );
            SELECT id INTO general_subcategory_id
            FROM subcategories
            WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'general'
            LIMIT 1;

            INSERT INTO brands (store_id, category_id, name, description, is_active)
            SELECT shop_store_id, leggings_category_id, 'Prisma', 'Leggings brand', true
            WHERE NOT EXISTS (
                SELECT 1 FROM brands
                WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'prisma'
            );
            INSERT INTO brands (store_id, category_id, name, description, is_active)
            SELECT shop_store_id, leggings_category_id, 'Fly Birds', 'Leggings brand', true
            WHERE NOT EXISTS (
                SELECT 1 FROM brands
                WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'fly birds'
            );
            SELECT id INTO prisma_brand_id FROM brands
            WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'prisma' LIMIT 1;
            SELECT id INTO fly_birds_brand_id FROM brands
            WHERE store_id = shop_store_id AND category_id = leggings_category_id AND lower(name) = 'fly birds' LIMIT 1;

            INSERT INTO products (store_id, category_id, subcategory_id, brand_id, sku, name, size, color, purchase_price, selling_price, pricing_type, mrp, current_stock, minimum_stock, product_date, unit, warehouse, is_active, is_test_data)
            SELECT shop_store_id, leggings_category_id, general_subcategory_id, prisma_brand_id, 'RF-LEG-PRISMA', 'Full Leggings', '3XL', 'Assorted', 386.22, 549.00, 'MRP', 549.00, 0, 0, CURRENT_DATE, 'Each', 'Main store', true, false
            WHERE NOT EXISTS (
                SELECT 1 FROM products WHERE store_id = shop_store_id AND category_id = leggings_category_id AND subcategory_id = general_subcategory_id AND brand_id = prisma_brand_id AND lower(name) = 'full leggings'
            );
            INSERT INTO products (store_id, category_id, subcategory_id, brand_id, sku, name, size, color, purchase_price, selling_price, pricing_type, mrp, current_stock, minimum_stock, product_date, unit, warehouse, is_active, is_test_data)
            SELECT shop_store_id, leggings_category_id, general_subcategory_id, fly_birds_brand_id, 'RF-LEG-FLY-BIRDS', 'Full Leggings', '3XL', 'Assorted', 351.04, 499.00, 'MRP', 499.00, 0, 0, CURRENT_DATE, 'Each', 'Main store', true, false
            WHERE NOT EXISTS (
                SELECT 1 FROM products WHERE store_id = shop_store_id AND category_id = leggings_category_id AND subcategory_id = general_subcategory_id AND brand_id = fly_birds_brand_id AND lower(name) = 'full leggings'
            );
            SELECT id INTO prisma_product_id FROM products WHERE store_id = shop_store_id AND category_id = leggings_category_id AND subcategory_id = general_subcategory_id AND brand_id = prisma_brand_id AND lower(name) = 'full leggings' LIMIT 1;
            SELECT id INTO fly_birds_product_id FROM products WHERE store_id = shop_store_id AND category_id = leggings_category_id AND subcategory_id = general_subcategory_id AND brand_id = fly_birds_brand_id AND lower(name) = 'full leggings' LIMIT 1;

            FOR line IN
                SELECT * FROM (VALUES
                    ('Prisma', '3XL', 2, 549.00::numeric, 386.22::numeric, 'RF-TEMP-PRISMA-3XL'),
                    ('Prisma', '2XL', 3, 549.00::numeric, 386.22::numeric, 'RF-TEMP-PRISMA-2XL'),
                    ('Prisma', 'XL', 8, 549.00::numeric, 386.22::numeric, 'RF-TEMP-PRISMA-XL'),
                    ('Prisma', 'L', 6, 499.00::numeric, 351.04::numeric, 'RF-TEMP-PRISMA-L'),
                    ('Prisma', 'M', 17, 499.00::numeric, 351.04::numeric, 'RF-TEMP-PRISMA-M'),
                    ('Prisma', 'S', 31, 499.00::numeric, 351.04::numeric, 'RF-TEMP-PRISMA-S'),
                    ('Fly Birds', '3XL', 16, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-3XL'),
                    ('Fly Birds', '2XL', 27, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-2XL'),
                    ('Fly Birds', 'XL', 8, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-XL'),
                    ('Fly Birds', 'L', 13, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-L'),
                    ('Fly Birds', 'M', 25, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-M'),
                    ('Fly Birds', 'S', 16, 499.00::numeric, 351.04::numeric, 'RF-TEMP-FLY-BIRDS-S')
                ) AS seeded(brand_name, size, quantity, mrp, purchase_cost, barcode)
            LOOP
                target_product_id := CASE WHEN line.brand_name = 'Prisma' THEN prisma_product_id ELSE fly_birds_product_id END;
                SELECT variant.id INTO variant_id FROM product_variants AS variant
                WHERE variant.store_id = shop_store_id AND variant.product_id = target_product_id AND lower(variant.size) = lower(line.size) AND lower(COALESCE(variant.color, '')) = 'assorted'
                LIMIT 1;
                IF variant_id IS NULL THEN
                    INSERT INTO product_variants (store_id, product_id, color, size, internal_sku, barcode, identity_key, mrp, selling_price, last_purchase_cost, average_cost, current_stock, classification_review_required, is_active)
                    VALUES (shop_store_id, target_product_id, 'Assorted', line.size, replace(line.barcode, 'RF-TEMP-', 'RF-'), line.barcode, concat(target_product_id, '|', lower(line.size), '|assorted|', lower(line.barcode)), line.mrp, line.mrp, line.purchase_cost, line.purchase_cost, 0, false, true)
                    RETURNING id INTO variant_id;
                END IF;

                INSERT INTO product_barcodes (id, store_id, product_id, product_variant_id, barcode, barcode_type, manufacturer_barcode, package_quantity, scan_unit, inventory_unit, base_unit_conversion, sale_mode, mrp, default_selling_price, active, verified, verified_by, verified_at)
                SELECT gen_random_uuid(), shop_store_id, target_product_id, variant_id, line.barcode, 'INTERNAL', false, 1, 'PIECE', 'PIECE', 1, 'PIECE_ONLY', line.mrp, line.mrp, true, true, owner_id, now()
                WHERE NOT EXISTS (SELECT 1 FROM product_barcodes WHERE store_id = shop_store_id AND barcode = line.barcode);
                INSERT INTO product_barcode_audits (id, store_id, barcode, old_product_variant_id, new_product_variant_id, action, reason, changed_by)
                SELECT gen_random_uuid(), shop_store_id, line.barcode, NULL, variant_id, 'TEMPORARY_INTERNAL_SEEDED', 'Opening stock entered before manufacturer label scanning', owner_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM product_barcode_audits
                    WHERE store_id = shop_store_id AND barcode = line.barcode AND action = 'TEMPORARY_INTERNAL_SEEDED'
                );

                IF NOT EXISTS (
                    SELECT 1 FROM stock_history
                    WHERE store_id = shop_store_id AND product_variant_id = variant_id AND movement_type = 'OPENING_STOCK' AND reference = opening_reference
                ) THEN
                    SELECT current_stock INTO variant_stock_before FROM product_variants WHERE id = variant_id FOR UPDATE;
                    SELECT current_stock INTO product_stock_before FROM products WHERE id = target_product_id FOR UPDATE;
                    INSERT INTO inventory_cost_lots (id, store_id, product_variant_id, received_quantity, remaining_quantity, unit_purchase_cost, allocated_landed_cost, effective_unit_cost, received_date, lot_reference)
                    VALUES (gen_random_uuid(), shop_store_id, variant_id, line.quantity, line.quantity, line.purchase_cost, 0, line.purchase_cost, now(), opening_reference || ' / ' || line.brand_name || ' ' || line.size);
                    UPDATE product_variants SET current_stock = variant_stock_before + line.quantity, last_purchase_cost = line.purchase_cost, average_cost = line.purchase_cost WHERE id = variant_id;
                    UPDATE products SET current_stock = product_stock_before + line.quantity WHERE id = target_product_id;
                    INSERT INTO product_inventory (id, product_id, store_id, current_stock, minimum_stock)
                    VALUES (gen_random_uuid(), target_product_id, shop_store_id, line.quantity, 0)
                    ON CONFLICT (product_id, store_id) DO UPDATE SET current_stock = product_inventory.current_stock + EXCLUDED.current_stock;
                    INSERT INTO stock_history (id, product_id, product_variant_id, store_id, movement_type, qty, before_stock, after_stock, reference, created_by, unit_cost)
                    VALUES (gen_random_uuid(), target_product_id, variant_id, shop_store_id, 'OPENING_STOCK', line.quantity, variant_stock_before, variant_stock_before + line.quantity, opening_reference, owner_id, line.purchase_cost);
                END IF;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Opening stock is an audited accounting event and must never be silently reversed by a schema downgrade.
    pass

INSERT INTO stores (id, name, code, address, phone)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Rainbow fashions',
    'MAIN',
    'Primary retail store',
    '+91-9000000000'
)
ON CONFLICT (code) DO UPDATE
SET
    name = EXCLUDED.name,
    address = EXCLUDED.address,
    phone = EXCLUDED.phone,
    is_active = TRUE;

INSERT INTO users (id, store_id, full_name, email, password_hash, role, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000101',
    '00000000-0000-0000-0000-000000000001',
    'Shop Owner',
    'Rainbow@fashions.com',
    crypt('Fashions123', gen_salt('bf', 12)),
    'OWNER',
    TRUE
)
ON CONFLICT (email) DO UPDATE
SET
    full_name = EXCLUDED.full_name,
    store_id = EXCLUDED.store_id,
    role = EXCLUDED.role,
    is_active = TRUE;

INSERT INTO categories (id, store_id, name, description)
VALUES
    ('00000000-0000-0000-0000-000000001001', '00000000-0000-0000-0000-000000000001', 'Kurty', 'Kurties and ethnic tops'),
    ('00000000-0000-0000-0000-000000001002', '00000000-0000-0000-0000-000000000001', 'Bra', 'Women innerwear bras'),
    ('00000000-0000-0000-0000-000000001003', '00000000-0000-0000-0000-000000000001', 'Leggins', 'Women leggings and stretch wear'),
    ('00000000-0000-0000-0000-000000001004', '00000000-0000-0000-0000-000000000001', 'Panties', 'Women innerwear panties')
ON CONFLICT (store_id, name) DO UPDATE
SET
    description = EXCLUDED.description,
    is_active = TRUE;

INSERT INTO brands (id, store_id, category_id, name, description)
VALUES
    ('00000000-0000-0000-0000-000000002001', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001003', 'Prisma', 'Fashion apparel brand'),
    ('00000000-0000-0000-0000-000000002002', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001001', 'Flybirds', 'Everyday clothing brand'),
    ('00000000-0000-0000-0000-000000002003', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001002', 'Jockey', 'Branded innerwear'),
    ('00000000-0000-0000-0000-000000002004', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001004', 'Jockey', 'Branded innerwear')
ON CONFLICT (store_id, category_id, name) DO UPDATE
SET
    description = EXCLUDED.description,
    is_active = TRUE;

INSERT INTO subcategories (id, store_id, category_id, name, description)
VALUES
    ('00000000-0000-0000-0000-000000005001', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001001', 'General', 'Default product group'),
    ('00000000-0000-0000-0000-000000005002', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001002', 'General', 'Default product group'),
    ('00000000-0000-0000-0000-000000005003', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001003', 'General', 'Default product group'),
    ('00000000-0000-0000-0000-000000005004', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000001004', 'General', 'Default product group')
ON CONFLICT (store_id, category_id, name) DO UPDATE SET description = EXCLUDED.description, is_active = TRUE;

INSERT INTO products (
    id,
    category_id,
    subcategory_id,
    brand_id,
    name,
    size,
    color,
    purchase_price,
    selling_price,
    pricing_type,
    mrp,
    current_stock,
    minimum_stock,
    barcode,
    product_date
)
VALUES
    (
        '00000000-0000-0000-0000-000000004001',
        '00000000-0000-0000-0000-000000001003',
        '00000000-0000-0000-0000-000000005003',
        '00000000-0000-0000-0000-000000002001',
        'Cotton Leggins',
        'M',
        'Black',
        180.00,
        299.00,
        'OWN_PRICE',
        349.00,
        24,
        8,
        '890000000001',
        CURRENT_DATE
    ),
    (
        '00000000-0000-0000-0000-000000004002',
        '00000000-0000-0000-0000-000000001003',
        '00000000-0000-0000-0000-000000005003',
        '00000000-0000-0000-0000-000000002001',
        'Cotton Leggins',
        'L',
        'Black',
        185.00,
        319.00,
        'OWN_PRICE',
        369.00,
        18,
        8,
        '890000000002',
        CURRENT_DATE
    ),
    (
        '00000000-0000-0000-0000-000000004003',
        '00000000-0000-0000-0000-000000001002',
        '00000000-0000-0000-0000-000000005002',
        '00000000-0000-0000-0000-000000002003',
        'Everyday Comfort Bra',
        '34B',
        'Skin',
        320.00,
        499.00,
        'MRP',
        499.00,
        12,
        6,
        '890000000003',
        CURRENT_DATE
    ),
    (
        '00000000-0000-0000-0000-000000004004',
        '00000000-0000-0000-0000-000000001001',
        '00000000-0000-0000-0000-000000005001',
        '00000000-0000-0000-0000-000000002002',
        'Printed Rayon Kurty',
        'XL',
        'Maroon',
        420.00,
        699.00,
        'OWN_PRICE',
        899.00,
        7,
        5,
        '890000000004',
        CURRENT_DATE
    ),
    (
        '00000000-0000-0000-0000-000000004005',
        '00000000-0000-0000-0000-000000001004',
        '00000000-0000-0000-0000-000000005004',
        '00000000-0000-0000-0000-000000002004',
        'Cotton Panties',
        'L',
        'White',
        90.00,
        149.00,
        'MRP',
        149.00,
        4,
        5,
        '890000000005',
        CURRENT_DATE
    )
ON CONFLICT (category_id, subcategory_id, brand_id, name, size, color) DO UPDATE
SET
    purchase_price = EXCLUDED.purchase_price,
    selling_price = EXCLUDED.selling_price,
    pricing_type = EXCLUDED.pricing_type,
    mrp = EXCLUDED.mrp,
    current_stock = EXCLUDED.current_stock,
    minimum_stock = EXCLUDED.minimum_stock,
    barcode = EXCLUDED.barcode,
    product_date = EXCLUDED.product_date,
    is_active = TRUE;

INSERT INTO product_inventory (product_id, store_id, current_stock, minimum_stock)
SELECT
    id,
    '00000000-0000-0000-0000-000000000001',
    current_stock,
    minimum_stock
FROM products
ON CONFLICT (product_id, store_id) DO UPDATE
SET
    current_stock = EXCLUDED.current_stock,
    minimum_stock = EXCLUDED.minimum_stock;

UPDATE products AS product
SET store_id = inventory.store_id
FROM product_inventory AS inventory
WHERE inventory.product_id = product.id
  AND product.store_id IS NULL;

INSERT INTO product_variants (
    id, store_id, product_id, color, size, style_code, internal_sku,
    barcode, identity_key, mrp, selling_price, last_purchase_cost,
    average_cost, current_stock, classification_review_required, is_active
)
SELECT
    gen_random_uuid(),
    product.store_id,
    product.id,
    product.color,
    product.size,
    'SEED',
    'SEED-' || replace(product.id::text, '-', ''),
    'VAR-' || replace(product.id::text, '-', ''),
    'seed|' || product.id::text,
    product.mrp,
    product.selling_price,
    product.purchase_price,
    product.purchase_price,
    inventory.current_stock,
    FALSE,
    TRUE
FROM products AS product
JOIN product_inventory AS inventory ON inventory.product_id = product.id
ON CONFLICT (store_id, identity_key) DO UPDATE
SET
    selling_price = EXCLUDED.selling_price,
    last_purchase_cost = EXCLUDED.last_purchase_cost,
    average_cost = EXCLUDED.average_cost,
    current_stock = EXCLUDED.current_stock,
    is_active = TRUE;

INSERT INTO inventory_cost_lots (
    id, store_id, product_variant_id, received_quantity, remaining_quantity,
    unit_purchase_cost, allocated_landed_cost, effective_unit_cost, lot_reference
)
SELECT
    gen_random_uuid(),
    variant.store_id,
    variant.id,
    variant.current_stock,
    variant.current_stock,
    variant.last_purchase_cost,
    0,
    variant.average_cost,
    'Seed inventory'
FROM product_variants AS variant
WHERE variant.current_stock > 0
  AND NOT EXISTS (
      SELECT 1
      FROM inventory_cost_lots AS lot
      WHERE lot.product_variant_id = variant.id
  );

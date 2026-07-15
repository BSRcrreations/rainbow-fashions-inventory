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

INSERT INTO categories (id, name, description)
VALUES
    ('00000000-0000-0000-0000-000000001001', 'Kurty', 'Kurties and ethnic tops'),
    ('00000000-0000-0000-0000-000000001002', 'Bra', 'Women innerwear bras'),
    ('00000000-0000-0000-0000-000000001003', 'Leggins', 'Women leggings and stretch wear'),
    ('00000000-0000-0000-0000-000000001004', 'Panties', 'Women innerwear panties')
ON CONFLICT (name) DO UPDATE
SET
    description = EXCLUDED.description,
    is_active = TRUE;

INSERT INTO brands (id, name, description)
VALUES
    ('00000000-0000-0000-0000-000000002001', 'Prisma', 'Fashion apparel brand'),
    ('00000000-0000-0000-0000-000000002002', 'Flybirds', 'Everyday clothing and innerwear brand'),
    ('00000000-0000-0000-0000-000000002003', 'Jockey', 'Branded innerwear and clothing')
ON CONFLICT (name) DO UPDATE
SET
    description = EXCLUDED.description,
    is_active = TRUE;

INSERT INTO suppliers (id, name, phone, email, gst_number, address)
VALUES
    (
        '00000000-0000-0000-0000-000000003001',
        'ARK Distributors',
        '+91-9111111111',
        'sales@arkdistributors.example',
        '29ABCDE1234F1Z5',
        'Wholesale Market Road'
    ),
    (
        '00000000-0000-0000-0000-000000003002',
        'GGL',
        '+91-9222222222',
        'orders@ggl.example',
        '29ABCDE5678F1Z5',
        'Industrial Area'
    )
ON CONFLICT (name) DO UPDATE
SET
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    gst_number = EXCLUDED.gst_number,
    address = EXCLUDED.address,
    is_active = TRUE;

INSERT INTO products (
    id,
    category_id,
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
    barcode
)
VALUES
    (
        '00000000-0000-0000-0000-000000004001',
        '00000000-0000-0000-0000-000000001003',
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
        '890000000001'
    ),
    (
        '00000000-0000-0000-0000-000000004002',
        '00000000-0000-0000-0000-000000001003',
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
        '890000000002'
    ),
    (
        '00000000-0000-0000-0000-000000004003',
        '00000000-0000-0000-0000-000000001002',
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
        '890000000003'
    ),
    (
        '00000000-0000-0000-0000-000000004004',
        '00000000-0000-0000-0000-000000001001',
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
        '890000000004'
    ),
    (
        '00000000-0000-0000-0000-000000004005',
        '00000000-0000-0000-0000-000000001004',
        '00000000-0000-0000-0000-000000002003',
        'Cotton Panties',
        'L',
        'White',
        90.00,
        149.00,
        'MRP',
        149.00,
        4,
        5,
        '890000000005'
    )
ON CONFLICT (category_id, brand_id, name, size, color) DO UPDATE
SET
    purchase_price = EXCLUDED.purchase_price,
    selling_price = EXCLUDED.selling_price,
    pricing_type = EXCLUDED.pricing_type,
    mrp = EXCLUDED.mrp,
    current_stock = EXCLUDED.current_stock,
    minimum_stock = EXCLUDED.minimum_stock,
    barcode = EXCLUDED.barcode,
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

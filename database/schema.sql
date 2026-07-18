CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('OWNER', 'MANAGER', 'STAFF');
CREATE TYPE pricing_type AS ENUM ('MRP', 'OWN_PRICE');
CREATE TYPE purchase_status AS ENUM ('DRAFT', 'REVIEWED', 'CONFIRMED', 'CANCELLED');
CREATE TYPE stock_movement_type AS ENUM ('PURCHASE', 'SALE', 'ADJUSTMENT');
CREATE TYPE upload_file_type AS ENUM ('INVOICE_IMAGE', 'INVOICE_PDF', 'PRODUCT_IMAGE');

CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    code VARCHAR(40) NOT NULL,
    address TEXT,
    phone VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_stores_code UNIQUE (code)
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'STAFF',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_categories_name UNIQUE (name)
);

CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_brands_name UNIQUE (name)
);

CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(180) NOT NULL,
    phone VARCHAR(30),
    email VARCHAR(255),
    gst_number VARCHAR(40),
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_suppliers_name UNIQUE (name)
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    sku VARCHAR(80),
    name VARCHAR(180) NOT NULL,
    size VARCHAR(60) NOT NULL,
    color VARCHAR(80) NOT NULL,
    purchase_price NUMERIC(12, 2) NOT NULL,
    selling_price NUMERIC(12, 2) NOT NULL,
    pricing_type pricing_type NOT NULL,
    mrp NUMERIC(12, 2),
    current_stock INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    barcode VARCHAR(80),
    image_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_products_purchase_price_non_negative CHECK (purchase_price >= 0),
    CONSTRAINT ck_products_selling_price_non_negative CHECK (selling_price >= 0),
    CONSTRAINT ck_products_mrp_non_negative CHECK (mrp IS NULL OR mrp >= 0),
    CONSTRAINT ck_products_current_stock_non_negative CHECK (current_stock >= 0),
    CONSTRAINT ck_products_minimum_stock_non_negative CHECK (minimum_stock >= 0),
    CONSTRAINT ck_products_mrp_required_for_mrp_pricing CHECK (
        pricing_type <> 'MRP' OR mrp IS NOT NULL
    ),
    CONSTRAINT uq_products_variant UNIQUE (category_id, brand_id, name, size, color),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT uq_products_barcode UNIQUE (barcode)
);

CREATE TABLE product_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    current_stock INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_product_inventory_current_stock_non_negative CHECK (current_stock >= 0),
    CONSTRAINT ck_product_inventory_minimum_stock_non_negative CHECK (minimum_stock >= 0),
    CONSTRAINT uq_product_inventory_product_store UNIQUE (product_id, store_id)
);

CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_type upload_file_type NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_uploaded_files_size_positive CHECK (file_size_bytes > 0),
    CONSTRAINT uq_uploaded_files_stored_filename UNIQUE (stored_filename)
);

CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    uploaded_file_id UUID REFERENCES uploaded_files(id) ON DELETE SET NULL,
    invoice_number VARCHAR(120),
    invoice_date DATE,
    supplier_name VARCHAR(180),
    status purchase_status NOT NULL DEFAULT 'DRAFT',
    extracted_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    reviewed_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    confirmed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_purchases_total_amount_non_negative CHECK (total_amount >= 0),
    CONSTRAINT ck_purchases_confirmed_fields CHECK (
        status <> 'CONFIRMED' OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)
    )
);

CREATE TABLE purchase_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    matched_product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    brand_name VARCHAR(120),
    category_name VARCHAR(120),
    product_name VARCHAR(180) NOT NULL,
    size VARCHAR(60) NOT NULL,
    color VARCHAR(80) NOT NULL,
    quantity INTEGER NOT NULL,
    purchase_price NUMERIC(12, 2) NOT NULL,
    mrp NUMERIC(12, 2),
    line_total NUMERIC(12, 2) NOT NULL,
    confidence NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_purchase_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_purchase_items_purchase_price_non_negative CHECK (purchase_price >= 0),
    CONSTRAINT ck_purchase_items_mrp_non_negative CHECK (mrp IS NULL OR mrp >= 0),
    CONSTRAINT ck_purchase_items_line_total_non_negative CHECK (line_total >= 0),
    CONSTRAINT ck_purchase_items_confidence_range CHECK (
        confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
    )
);

CREATE TABLE stock_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    movement_type stock_movement_type NOT NULL,
    qty INTEGER NOT NULL,
    before_stock INTEGER NOT NULL,
    after_stock INTEGER NOT NULL,
    reference VARCHAR(180),
    purchase_id UUID REFERENCES purchases(id) ON DELETE SET NULL,
    purchase_item_id UUID REFERENCES purchase_items(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    movement_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_stock_history_qty_positive CHECK (qty > 0),
    CONSTRAINT ck_stock_history_before_stock_non_negative CHECK (before_stock >= 0),
    CONSTRAINT ck_stock_history_after_stock_non_negative CHECK (after_stock >= 0)
);

CREATE INDEX ix_users_store_id ON users(store_id);
CREATE INDEX ix_categories_name ON categories(name);
CREATE INDEX ix_brands_name ON brands(name);
CREATE INDEX ix_suppliers_name ON suppliers(name);
CREATE INDEX ix_products_category_id ON products(category_id);
CREATE INDEX ix_products_brand_id ON products(brand_id);
CREATE INDEX ix_products_sku ON products(sku);
CREATE INDEX ix_products_name ON products(name);
CREATE INDEX ix_products_color ON products(color);
CREATE INDEX ix_products_size ON products(size);
CREATE INDEX ix_products_barcode ON products(barcode);
CREATE INDEX ix_products_search ON products USING gin (
    to_tsvector('simple', coalesce(sku, '') || ' ' || coalesce(name, '') || ' ' || coalesce(size, '') || ' ' || coalesce(color, '') || ' ' || coalesce(barcode, ''))
);
CREATE INDEX ix_product_inventory_store_id ON product_inventory(store_id);
CREATE INDEX ix_uploaded_files_uploaded_by ON uploaded_files(uploaded_by);
CREATE INDEX ix_purchases_store_id ON purchases(store_id);
CREATE INDEX ix_purchases_supplier_id ON purchases(supplier_id);
CREATE INDEX ix_purchases_status ON purchases(status);
CREATE INDEX ix_purchases_invoice_number ON purchases(invoice_number);
CREATE INDEX ix_purchases_invoice_date ON purchases(invoice_date);
CREATE INDEX ix_purchases_created_at ON purchases(created_at);
CREATE INDEX ix_purchase_items_purchase_id ON purchase_items(purchase_id);
CREATE INDEX ix_purchase_items_product_id ON purchase_items(product_id);
CREATE INDEX ix_purchase_items_matched_product_id ON purchase_items(matched_product_id);
CREATE INDEX ix_stock_history_product_id ON stock_history(product_id);
CREATE INDEX ix_stock_history_store_id ON stock_history(store_id);
CREATE INDEX ix_stock_history_movement_type ON stock_history(movement_type);
CREATE INDEX ix_stock_history_movement_date ON stock_history(movement_date);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_stores_updated_at
BEFORE UPDATE ON stores
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_categories_updated_at
BEFORE UPDATE ON categories
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_brands_updated_at
BEFORE UPDATE ON brands
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_suppliers_updated_at
BEFORE UPDATE ON suppliers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_product_inventory_updated_at
BEFORE UPDATE ON product_inventory
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_purchases_updated_at
BEFORE UPDATE ON purchases
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_purchase_items_updated_at
BEFORE UPDATE ON purchase_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

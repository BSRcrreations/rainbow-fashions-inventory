CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('OWNER', 'MANAGER', 'STAFF');
CREATE TYPE pricing_type AS ENUM ('MRP', 'OWN_PRICE');
CREATE TYPE purchase_status AS ENUM ('DRAFT', 'REVIEWED', 'CONFIRMED', 'CANCELLED');
CREATE TYPE stock_movement_type AS ENUM ('PURCHASE', 'SALE', 'CUSTOMER_RETURN', 'SUPPLIER_RETURN', 'DAMAGE', 'MANUAL_ADJUSTMENT', 'SALE_EDIT_RETURN', 'SALE_EDIT_DECREASE', 'SALE_VOID', 'PURCHASE_VOID', 'OPENING_STOCK', 'STOCK_RESET_OUT', 'STOCK_COUNT_IN', 'STOCK_COUNT_OUT');
CREATE TYPE upload_file_type AS ENUM ('INVOICE_IMAGE', 'INVOICE_PDF', 'PRODUCT_IMAGE');
CREATE TYPE document_job_status AS ENUM ('UPLOADED', 'QUEUED', 'PREPROCESSING', 'OCR_RUNNING', 'AI_EXTRACTION', 'PRODUCT_MATCHING', 'VALIDATING', 'REVIEW_REQUIRED', 'COMPLETED', 'FAILED');

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
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_categories_store_name UNIQUE (store_id, name)
);

CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_brands_store_category_name UNIQUE (store_id, category_id, name),
    CONSTRAINT uq_brands_id_category UNIQUE (id, category_id)
);

CREATE TABLE subcategories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_subcategories_store_category_name UNIQUE (store_id, category_id, name),
    CONSTRAINT uq_subcategories_id_category UNIQUE (id, category_id)
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
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    subcategory_id UUID NOT NULL REFERENCES subcategories(id) ON DELETE RESTRICT,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    sku VARCHAR(80),
    name VARCHAR(180) NOT NULL,
    size VARCHAR(60),
    color VARCHAR(80),
    purchase_price NUMERIC(12, 2) NOT NULL,
    selling_price NUMERIC(12, 2) NOT NULL,
    pricing_type pricing_type NOT NULL,
    mrp NUMERIC(12, 2),
    gst_rate NUMERIC(5, 2),
    hsn_code VARCHAR(20),
    current_stock INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    barcode VARCHAR(80),
    product_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT,
    hsn_sac VARCHAR(40),
    unit VARCHAR(40) NOT NULL DEFAULT 'Each',
    warehouse VARCHAR(120),
    image_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_test_data BOOLEAN NOT NULL DEFAULT FALSE,
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
    CONSTRAINT fk_products_subcategory_category FOREIGN KEY (subcategory_id, category_id) REFERENCES subcategories(id, category_id) ON DELETE RESTRICT,
    CONSTRAINT fk_products_brand_category FOREIGN KEY (brand_id, category_id) REFERENCES brands(id, category_id) ON DELETE RESTRICT,
    CONSTRAINT uq_products_catalog_variant UNIQUE (category_id, subcategory_id, brand_id, name, size, color),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT uq_products_barcode UNIQUE (barcode)
);

CREATE TABLE product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    color VARCHAR(80),
    size VARCHAR(60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_product_variants_combination UNIQUE (product_id, color, size)
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

CREATE TABLE purchase_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    uploaded_file_id UUID NOT NULL REFERENCES uploaded_files(id) ON DELETE RESTRICT,
    sha256 VARCHAR(64) NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_purchase_documents_store_id ON purchase_documents(store_id);
CREATE INDEX ix_purchase_documents_sha256 ON purchase_documents(sha256);

CREATE TABLE document_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES purchase_documents(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    status document_job_status NOT NULL DEFAULT 'QUEUED',
    progress INTEGER NOT NULL DEFAULT 0,
    message VARCHAR(240) NOT NULL DEFAULT 'Queued for invoice recognition',
    request_id VARCHAR(36) NOT NULL,
    provider VARCHAR(40) NOT NULL DEFAULT 'mock',
    result JSONB,
    error_code VARCHAR(80),
    error_message VARCHAR(300),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_document_processing_jobs_document_id ON document_processing_jobs(document_id);
CREATE INDEX ix_document_processing_jobs_store_id ON document_processing_jobs(store_id);
CREATE INDEX ix_document_processing_jobs_request_id ON document_processing_jobs(request_id);

CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    uploaded_file_id UUID REFERENCES uploaded_files(id) ON DELETE SET NULL,
    purchase_document_id UUID REFERENCES purchase_documents(id) ON DELETE SET NULL UNIQUE,
    processing_job_id UUID REFERENCES document_processing_jobs(id) ON DELETE SET NULL,
    invoice_number VARCHAR(120),
    purchase_date DATE NOT NULL DEFAULT CURRENT_DATE,
    invoice_date DATE,
    received_date DATE,
    due_date DATE,
    supplier_name VARCHAR(180),
    payment_mode VARCHAR(40) NOT NULL DEFAULT 'CREDIT',
    amount_paid NUMERIC(12, 2) NOT NULL DEFAULT 0,
    place_of_supply VARCHAR(120),
    purchase_reference VARCHAR(120),
    notes VARCHAR(1000),
    warehouse VARCHAR(120),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    status purchase_status NOT NULL DEFAULT 'DRAFT',
    extracted_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    reviewed_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    packaging_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    freight_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    round_off NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    image_hash VARCHAR(64),
    ai_processing_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    version INTEGER NOT NULL DEFAULT 1,
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
    proposed_product_name VARCHAR(180),
    barcode VARCHAR(80),
    supplier_product_code VARCHAR(120),
    hsn_sac VARCHAR(40),
    unit VARCHAR(40) NOT NULL DEFAULT 'Each',
    size VARCHAR(60) NOT NULL,
    color VARCHAR(80) NOT NULL,
    quantity INTEGER NOT NULL,
    purchase_price NUMERIC(12, 2) NOT NULL,
    discount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    mrp NUMERIC(12, 2),
    selling_price NUMERIC(12, 2),
    line_total NUMERIC(12, 2) NOT NULL,
    confidence NUMERIC(5, 4),
    match_status VARCHAR(40) NOT NULL DEFAULT 'NOT_FOUND',
    batch_number VARCHAR(120),
    manufacturing_date DATE,
    expiry_date DATE,
    create_new_product BOOLEAN NOT NULL DEFAULT FALSE,
    variant_attributes JSONB NOT NULL DEFAULT '{}'::JSONB,
    classification_verified BOOLEAN NOT NULL DEFAULT FALSE,
    classification_verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    classification_verified_at TIMESTAMPTZ,
    user_verified BOOLEAN NOT NULL DEFAULT FALSE,
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

CREATE TABLE purchase_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    action VARCHAR(80) NOT NULL,
    reason VARCHAR(500),
    before_data JSONB,
    after_data JSONB,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_purchase_audits_purchase_id ON purchase_audits(purchase_id);

CREATE TABLE sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    invoice_number VARCHAR(120) NOT NULL,
    customer_name VARCHAR(180),
    payment_mode VARCHAR(40) NOT NULL,
    cashier_id UUID REFERENCES users(id) ON DELETE SET NULL,
    subtotal NUMERIC(12, 2) NOT NULL,
    discount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12, 2) NOT NULL,
    cost_amount NUMERIC(12, 2) NOT NULL,
    profit_amount NUMERIC(12, 2) NOT NULL,
    sale_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    version INTEGER NOT NULL DEFAULT 1,
    edited_at TIMESTAMPTZ,
    edited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    edit_reason VARCHAR(300),
    voided_at TIMESTAMPTZ,
    voided_by UUID REFERENCES users(id) ON DELETE SET NULL,
    void_reason VARCHAR(300),
    CONSTRAINT uq_sales_invoice_number UNIQUE (invoice_number),
    CONSTRAINT ck_sales_amounts_non_negative CHECK (subtotal >= 0 AND discount >= 0 AND total_amount >= 0 AND cost_amount >= 0),
    CONSTRAINT ck_sales_discount_not_above_subtotal CHECK (discount <= subtotal)
);

CREATE TABLE sale_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    product_variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    product_name VARCHAR(180) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL,
    sku_snapshot VARCHAR(80),
    barcode_snapshot VARCHAR(80),
    size_snapshot VARCHAR(60),
    color_snapshot VARCHAR(80),
    style_snapshot VARCHAR(80),
    mrp_snapshot NUMERIC(12, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_sale_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_sale_items_amounts_non_negative CHECK (unit_price >= 0 AND unit_cost >= 0 AND line_total >= 0)
);

CREATE TABLE sale_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    action VARCHAR(40) NOT NULL,
    reason VARCHAR(300),
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sale_returns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id UUID NOT NULL REFERENCES sales(id) ON DELETE RESTRICT,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE RESTRICT,
    reason VARCHAR(300) NOT NULL,
    refund_method VARCHAR(40),
    refund_amount NUMERIC(12, 2) NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sale_return_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_return_id UUID NOT NULL REFERENCES sale_returns(id) ON DELETE CASCADE,
    sale_item_id UUID NOT NULL REFERENCES sale_items(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    refund_amount NUMERIC(12, 2) NOT NULL
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
    request_id VARCHAR(120),
    purchase_id UUID REFERENCES purchases(id) ON DELETE SET NULL,
    purchase_item_id UUID REFERENCES purchase_items(id) ON DELETE SET NULL,
    sale_id UUID REFERENCES sales(id) ON DELETE SET NULL,
    sale_item_id UUID REFERENCES sale_items(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    movement_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_stock_history_qty_positive CHECK (qty > 0),
    CONSTRAINT ck_stock_history_before_stock_non_negative CHECK (before_stock >= 0),
    CONSTRAINT ck_stock_history_after_stock_non_negative CHECK (after_stock >= 0)
);

CREATE TABLE stock_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(80) NOT NULL,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE RESTRICT,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_role VARCHAR(32),
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    product_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    previous_quantity INTEGER,
    adjustment_quantity INTEGER,
    resulting_quantity INTEGER,
    request_id VARCHAR(120) NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_users_store_id ON users(store_id);
CREATE INDEX ix_categories_name ON categories(name);
CREATE INDEX ix_brands_name ON brands(name);
CREATE INDEX ix_brands_category_id ON brands(category_id);
CREATE INDEX ix_subcategories_category_id ON subcategories(category_id);
CREATE INDEX ix_subcategories_name ON subcategories(name);
CREATE INDEX ix_suppliers_name ON suppliers(name);
CREATE INDEX ix_products_category_id ON products(category_id);
CREATE INDEX ix_products_store_id ON products(store_id);
CREATE INDEX ix_products_brand_id ON products(brand_id);
CREATE INDEX ix_products_subcategory_id ON products(subcategory_id);
CREATE INDEX ix_products_sku ON products(sku);
CREATE INDEX ix_products_name ON products(name);
CREATE INDEX ix_products_color ON products(color);
CREATE INDEX ix_products_size ON products(size);
CREATE INDEX ix_products_barcode ON products(barcode);
CREATE INDEX ix_products_is_test_data ON products(is_test_data);
CREATE INDEX ix_product_variants_product_id ON product_variants(product_id);
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
CREATE INDEX ix_purchases_purchase_date ON purchases(purchase_date);
-- Bring the bootstrap schema in line with the current application models.
ALTER TABLE stores
    ADD COLUMN allow_test_data_purge BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE purchases
    ADD COLUMN invoice_discount_type VARCHAR(40) NOT NULL DEFAULT 'NONE',
    ADD COLUMN invoice_discount_percentage NUMERIC(7, 4) NOT NULL DEFAULT 0,
    ADD COLUMN invoice_discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN invoice_discount_reason VARCHAR(500),
    ADD COLUMN invoice_discount_allocation_method VARCHAR(40) NOT NULL DEFAULT 'BY_ITEM_VALUE',
    ADD COLUMN invoice_tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0;

ALTER TABLE purchase_items
    ADD COLUMN product_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    ADD COLUMN internal_sku VARCHAR(120),
    ADD COLUMN style_code VARCHAR(80),
    ADD COLUMN list_unit_price NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN invoiced_unit_price NUMERIC(18, 2),
    ADD COLUMN discount_type VARCHAR(40) NOT NULL DEFAULT 'NONE',
    ADD COLUMN discount_percentage NUMERIC(7, 4) NOT NULL DEFAULT 0,
    ADD COLUMN discount_per_unit NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN discount_reason VARCHAR(500),
    ADD COLUMN discount_source VARCHAR(40) NOT NULL DEFAULT 'INVOICE_EXTRACTED',
    ADD COLUMN free_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ADD COLUMN chargeable_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ADD COLUMN accepted_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ADD COLUMN gross_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN taxable_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN net_line_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN effective_unit_cost NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN landed_unit_cost NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN allocated_invoice_discount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN promotion_id UUID,
    ADD COLUMN discount_rule_id UUID,
    ADD COLUMN discount_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN discount_verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN discount_verified_at TIMESTAMPTZ;

ALTER TABLE product_variants
    ADD COLUMN store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    ADD COLUMN style_code VARCHAR(80),
    ADD COLUMN model_number VARCHAR(120),
    ADD COLUMN manufacturer_sku VARCHAR(120),
    ADD COLUMN internal_sku VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN barcode VARCHAR(80) NOT NULL DEFAULT '',
    ADD COLUMN identity_key VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN mrp NUMERIC(12, 2),
    ADD COLUMN selling_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN last_purchase_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN average_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN current_stock INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN classification_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE product_variants DROP CONSTRAINT uq_product_variants_combination;
ALTER TABLE product_variants
    ADD CONSTRAINT uq_product_variants_store_identity UNIQUE (store_id, identity_key),
    ADD CONSTRAINT uq_product_variants_store_internal_sku UNIQUE (store_id, internal_sku),
    ADD CONSTRAINT uq_product_variants_store_barcode UNIQUE (store_id, barcode);

ALTER TABLE stock_history
    ADD COLUMN product_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    ADD COLUMN purchase_cost_lot_id UUID,
    ADD COLUMN unit_cost NUMERIC(12, 2);

CREATE TABLE inventory_cost_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    product_variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    purchase_id UUID REFERENCES purchases(id) ON DELETE SET NULL,
    purchase_item_id UUID UNIQUE REFERENCES purchase_items(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    received_quantity INTEGER NOT NULL,
    remaining_quantity INTEGER NOT NULL,
    unit_purchase_cost NUMERIC(12, 2) NOT NULL,
    allocated_landed_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    effective_unit_cost NUMERIC(12, 2) NOT NULL,
    received_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lot_reference VARCHAR(180),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE stock_history
    ADD CONSTRAINT fk_stock_history_purchase_cost_lot_id
    FOREIGN KEY (purchase_cost_lot_id) REFERENCES inventory_cost_lots(id) ON DELETE SET NULL;

CREATE INDEX ix_purchases_received_date ON purchases(received_date);
CREATE INDEX ix_purchases_image_hash ON purchases(image_hash);
CREATE INDEX ix_purchases_created_at ON purchases(created_at);
CREATE INDEX ix_purchase_items_purchase_id ON purchase_items(purchase_id);
CREATE INDEX ix_purchase_items_product_id ON purchase_items(product_id);
CREATE INDEX ix_purchase_items_matched_product_id ON purchase_items(matched_product_id);
CREATE INDEX ix_purchase_items_barcode ON purchase_items(barcode);
CREATE INDEX ix_purchase_items_product_variant_id ON purchase_items(product_variant_id);
CREATE INDEX ix_product_variants_store_id ON product_variants(store_id);
CREATE INDEX ix_inventory_cost_lots_store_id ON inventory_cost_lots(store_id);
CREATE INDEX ix_inventory_cost_lots_product_variant_id ON inventory_cost_lots(product_variant_id);
CREATE INDEX ix_stock_history_product_id ON stock_history(product_id);
CREATE INDEX ix_stock_history_store_id ON stock_history(store_id);
CREATE INDEX ix_stock_history_movement_type ON stock_history(movement_type);
CREATE INDEX ix_stock_history_movement_date ON stock_history(movement_date);
CREATE INDEX ix_stock_history_request_id ON stock_history(request_id);
CREATE INDEX ix_stock_history_product_variant_id ON stock_history(product_variant_id);
CREATE INDEX ix_stock_history_purchase_cost_lot_id ON stock_history(purchase_cost_lot_id);
CREATE INDEX ix_stock_audit_events_event_type ON stock_audit_events(event_type);
CREATE INDEX ix_stock_audit_events_store_id ON stock_audit_events(store_id);
CREATE INDEX ix_stock_audit_events_user_id ON stock_audit_events(user_id);
CREATE INDEX ix_stock_audit_events_product_id ON stock_audit_events(product_id);
CREATE INDEX ix_stock_audit_events_product_variant_id ON stock_audit_events(product_variant_id);
CREATE INDEX ix_stock_audit_events_request_id ON stock_audit_events(request_id);
CREATE INDEX ix_stock_audit_events_created_at ON stock_audit_events(created_at);
CREATE INDEX ix_sales_sale_date ON sales(sale_date);
CREATE INDEX ix_sales_invoice_number ON sales(invoice_number);
CREATE INDEX ix_sales_customer_name ON sales(customer_name);
CREATE INDEX ix_sales_payment_mode ON sales(payment_mode);
CREATE INDEX ix_sales_cashier_id ON sales(cashier_id);
CREATE INDEX ix_sales_status ON sales(status);
CREATE INDEX ix_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX ix_sale_items_product_id ON sale_items(product_id);
CREATE INDEX ix_sale_items_product_variant_id ON sale_items(product_variant_id);
CREATE INDEX ix_sale_audits_sale_id ON sale_audits(sale_id);
CREATE INDEX ix_sale_returns_sale_id ON sale_returns(sale_id);
CREATE INDEX ix_sale_returns_store_id ON sale_returns(store_id);
CREATE INDEX ix_sale_return_items_sale_return_id ON sale_return_items(sale_return_id);
CREATE INDEX ix_sale_return_items_sale_item_id ON sale_return_items(sale_item_id);
CREATE INDEX ix_stock_history_sale_id ON stock_history(sale_id);

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

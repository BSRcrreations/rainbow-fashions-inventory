export type UserRole = "OWNER" | "MANAGER" | "STAFF";
export type PricingType = "MRP" | "OWN_PRICE";
export type PurchaseStatus = "DRAFT" | "REVIEWED" | "CONFIRMED" | "CANCELLED" | "VOIDED";
export type StockMovementType = "PURCHASE" | "SALE" | "CUSTOMER_RETURN" | "SUPPLIER_RETURN" | "DAMAGE" | "MANUAL_ADJUSTMENT" | "SALE_EDIT_RETURN" | "SALE_EDIT_DECREASE" | "SALE_VOID" | "PURCHASE_VOID" | "OPENING_STOCK" | "STOCK_RESET_OUT" | "STOCK_COUNT_IN" | "STOCK_COUNT_OUT";
export type StockScanMode = "PURCHASE_RECEIVING" | "OPENING_STOCK" | "PHYSICAL_COUNT" | "STOCK_ADJUSTMENT" | "STOCK_TRANSFER";
export type StockScanStatus = "DRAFT" | "IN_PROGRESS" | "REVIEW_REQUIRED" | "CONFIRMED" | "CANCELLED";
export type StockScanQuantityMode = "INCREMENT" | "QUANTITY_ENTRY";
export type SaleStatus = "DRAFT" | "CANCELLED" | "COMPLETED" | "EDITED" | "PARTIALLY_RETURNED" | "RETURNED" | "VOIDED";

export interface User {
  id: string;
  store_id: string | null;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Category {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Brand {
  id: string;
  category_id: string;
  name: string;
  description?: string | null;
  logo_url?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubCategory {
  id: string;
  category_id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryHierarchy extends Category {
  brands: Brand[];
  subcategories: SubCategory[];
}

export interface Product {
  id: string;
  category_id: string;
  subcategory_id: string;
  brand_id: string;
  sku?: string | null;
  name: string;
  size?: string | null;
  color?: string | null;
  variants: ProductVariant[];
  purchase_price: string;
  selling_price: string;
  pricing_type: PricingType;
  mrp?: string | null;
  current_stock: number;
  minimum_stock: number;
  barcode?: string | null;
  product_date: string;
  description?: string | null;
  hsn_sac?: string | null;
  image_url?: string | null;
  is_active: boolean;
  is_test_data: boolean;
  category?: Category | null;
  subcategory?: SubCategory | null;
  brand?: Brand | null;
  brand_name?: string | null;
  brand_logo_url?: string | null;
  category_name?: string | null;
  variant_count?: number;
  total_stock?: number;
}

export interface ProductVariant {
  id: string;
  store_id: string;
  product_id: string;
  color?: string | null;
  size?: string | null;
  style_code?: string | null;
  model_number?: string | null;
  manufacturer_sku?: string | null;
  internal_sku: string;
  barcode: string;
  identity_key: string;
  mrp?: string | null;
  selling_price: string;
  last_purchase_cost: string;
  average_cost: string;
  current_stock: number;
  classification_review_required: boolean;
  is_active: boolean;
  scan_unit?: "PIECE" | "PACK";
  pieces_per_pack?: number;
  barcodes?: string[];
  created_at: string;
  updated_at: string;
}

export interface ProductVariantBarcode {
  product_id: string;
  variant_id: string;
  product_name: string;
  category?: string | null;
  category_id?: string | null;
  brand?: string | null;
  brand_id?: string | null;
  size?: string | null;
  color?: string | null;
  style_code?: string | null;
  sku: string;
  barcode: string;
  mrp?: string | null;
  selling_price: string;
  current_physical_stock: number;
  current_available_stock: number;
  active: boolean;
  package_quantity: number;
  scan_unit: string;
  inventory_unit: string;
  base_unit_conversion: number;
  sale_mode: string;
}

export interface BarcodeTransferVariantSummary {
  product_id: string;
  variant_id: string;
  store_id: string;
  product_name: string;
  brand_name?: string | null;
  size?: string | null;
  color?: string | null;
  style_code?: string | null;
  current_stock: number;
}

export interface BarcodeTransferLine {
  barcode: string;
  barcode_id: string;
  source_variant_id: string;
  target_variant_id: string;
  draft_session_item_ids: string[];
  confirmed_session_item_ids: string[];
  confirmed_quantity: number;
  completed_sale_count: number;
  completed_purchase_count: number;
  audit_id?: string | null;
}

export interface BulkBarcodeTransferPreview {
  barcodes: string[];
  source: BarcodeTransferVariantSummary;
  target: BarcodeTransferVariantSummary;
  lines: BarcodeTransferLine[];
  draft_only: boolean;
  source_stock_delta: number;
  target_stock_delta: number;
  net_stock_delta: number;
  confirmation_phrase: string;
  correction_stock_history_ids?: string[];
  audit_ids?: string[];
}

export interface LabelExtractionSuggestion {
  value: string;
  confidence: number;
  source_text: string;
  bounding_box?: Record<string, number> | null;
  requires_review: boolean;
}

export interface BarcodeImageResolution {
  image_url: string;
  suggestions: Record<string, LabelExtractionSuggestion>;
}

export interface StockScanSessionItem {
  id: string;
  product_id: string;
  product_variant_id: string;
  product_barcode_id?: string | null;
  barcode: string;
  product_name: string;
  category_name?: string | null;
  brand_name?: string | null;
  size?: string | null;
  color?: string | null;
  style_code?: string | null;
  sku?: string | null;
  mrp?: string | null;
  selling_price?: string | null;
  current_physical_stock: number;
  scanned_quantity: number;
  package_quantity: number;
  base_quantity: number;
  expected_quantity?: number | null;
  difference_quantity?: number | null;
  unit_cost?: string | null;
  condition: string;
  last_scanned_at: string;
  created_at: string;
}

export interface StockScanSession {
  id: string;
  store_id: string;
  mode: StockScanMode;
  status: StockScanStatus;
  quantity_mode: StockScanQuantityMode;
  purchase_id?: string | null;
  supplier_id?: string | null;
  default_category_id?: string | null;
  default_brand_id?: string | null;
  entry_date?: string | null;
  default_purchase_cost?: string | null;
  default_selling_price?: string | null;
  quick_post: boolean;
  location_name: string;
  source_location_name?: string | null;
  destination_location_name?: string | null;
  reference?: string | null;
  notes?: string | null;
  created_by: string;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
  updated_at: string;
  items: StockScanSessionItem[];
}

export interface SaleCatalogVariant {
  variant_id: string;
  product_id: string;
  size?: string | null;
  color?: string | null;
  style_code?: string | null;
  sku: string;
  barcode: string;
  mrp?: string | null;
  selling_price: string;
  available_stock: number;
  classification_review_required: boolean;
  is_active: boolean;
  scan_unit?: "PIECE" | "PACK";
  pieces_per_pack?: number;
}

export interface SaleCatalogProduct {
  product_id: string;
  name: string;
  category_name?: string | null;
  subcategory_name?: string | null;
  brand_name?: string | null;
  brand_logo_url?: string | null;
  product_image_url?: string | null;
  variant_count: number;
  total_stock: number;
  minimum_stock: number;
  total_available_stock: number;
  variants: SaleCatalogVariant[];
}

export interface SaleItem {
  id: string;
  product_id: string;
  product_variant_id?: string | null;
  product_name: string;
  barcode?: string | null;
  supplier_product_code?: string | null;
  unit: string;
  quantity: number;
  unit_price: string;
  unit_cost: string;
  line_total: string;
  sku_snapshot?: string | null;
  barcode_snapshot?: string | null;
  size_snapshot?: string | null;
  color_snapshot?: string | null;
  style_snapshot?: string | null;
  mrp_snapshot?: string | null;
}

export interface Sale {
  id: string;
  invoice_number: string;
  customer_id?: string | null;
  customer_name?: string | null;
  payment_mode: string;
  subtotal: string;
  discount: string;
  discount_type: "PERCENTAGE" | "FIXED_AMOUNT";
  discount_value: string;
  discount_amount: string;
  total_amount: string;
  grand_total: string;
  cost_amount: string;
  profit_amount: string;
  status: SaleStatus;
  version: number;
  edit_reason?: string | null;
  void_reason?: string | null;
  sale_date: string;
  cashier?: { id: string; full_name: string } | null;
  items: SaleItem[];
}

export interface SaleReturn {
  id: string;
  reason: string;
  refund_method?: string | null;
  refund_amount: string;
  created_at: string;
  items: Array<{ id: string; sale_item_id: string; quantity: number; refund_amount: string }>;
}

export interface SaleAudit {
  id: string;
  action: string;
  reason?: string | null;
  performed_by?: string | null;
  before_data?: Record<string, unknown> | null;
  after_data?: Record<string, unknown> | null;
  created_at: string;
}

export interface PaginatedSales {
  items: Sale[];
  meta: { page: number; page_size: number; total_records: number; total_pages: number };
}

export interface SalesMetric {
  sales: string;
  profit: string;
  orders: number;
}

export interface SalesDashboard {
  range_start: string;
  range_end: string;
  selected: SalesMetric;
  today: SalesMetric;
  yesterday: SalesMetric;
  week: SalesMetric;
  month: SalesMetric;
  total_revenue: string;
  collection: { cash: string; upi: string; card: string; other: string; total: string };
  inventory_value: string;
  total_stock: number;
  total_products: number;
  trend: Array<{ date: string; sales: string; profit: string; orders: number }>;
  top_categories: Array<{ id?: string | null; name: string; quantity: number; revenue: string }>;
  top_brands: Array<{ id?: string | null; name: string; quantity: number; revenue: string }>;
  top_products: Array<{ id?: string | null; name: string; quantity: number; revenue: string }>;
  recent_sales: Sale[];
  low_stock: Array<{ id: string; name: string; current_stock: number; minimum_stock: number }>;
  out_of_stock: Array<{ id: string; name: string; current_stock: number; minimum_stock: number }>;
}

export interface InventoryValuation {
  inventory_value: string;
}

export interface PaginatedProducts {
  items: Product[];
  meta: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export type StockResetScope = "SELECTED_VARIANTS" | "PRODUCT" | "CATEGORY" | "BRAND" | "ALL_CURRENT_STOCK" | "ALL_OPENING_STOCK";

export interface StockResetPreviewItem {
  variant_id: string;
  product_id: string;
  product: string;
  brand?: string | null;
  category?: string | null;
  size?: string | null;
  color?: string | null;
  barcode: string;
  sku: string;
  current_stock: number;
  reset_quantity: number;
  resulting_stock: number;
  unit_cost: string;
  inventory_value: string;
}

export interface StockResetPreviewResponse {
  variants: StockResetPreviewItem[];
  total_products: number;
  total_variants: number;
  total_pieces: number;
  total_inventory_value: string;
  request_id: string;
  classification_warning?: string | null;
}

export interface StockResetResponse extends StockResetPreviewResponse {
  stock_history_ids: string[];
  already_completed: boolean;
}

export type VariantCorrectionReason = "WRONG_SIZE_ENTERED" | "INCORRECT_VARIANT_SELECTED" | "INCORRECT_BARCODE_ASSIGNMENT" | "DATA_ENTRY_MISTAKE" | "TEST_DATA" | "OTHER";

export interface VariantCorrectionVariant {
  variant_id: string;
  product_id: string;
  product_name: string;
  size?: string | null;
  color?: string | null;
  sku: string;
  barcode: string;
  before_stock: number;
  after_stock: number;
}

export interface VariantCorrectionPreview {
  source: VariantCorrectionVariant;
  destination: VariantCorrectionVariant;
  quantity: number;
  reason: string;
  notes?: string | null;
  reference: string;
  request_id: string;
}

export interface VariantCorrectionResult extends VariantCorrectionPreview {
  source_history_id: string;
  destination_history_id: string;
  already_completed: boolean;
}

export interface PurchaseItem {
  id?: string;
  product_id?: string | null;
  matched_product_id?: string | null;
  product_variant_id?: string | null;
  category_id?: string | null;
  brand_id?: string | null;
  brand_name?: string | null;
  category_name?: string | null;
  product_name: string;
  proposed_product_name?: string | null;
  barcode?: string | null;
  supplier_product_code?: string | null;
  internal_sku?: string | null;
  style_code?: string | null;
  hsn_sac?: string | null;
  unit: string;
  size: string;
  color: string;
  quantity: number;
  purchase_price: string;
  discount: string;
  list_unit_price?: string;
  invoiced_unit_price?: string | null;
  discount_type?: "NONE" | "PERCENTAGE" | "FIXED_PER_UNIT" | "FIXED_PER_LINE" | "FINAL_UNIT_PRICE" | "QUANTITY_SLAB" | "FREE_QUANTITY" | "MANUAL";
  discount_percentage?: string;
  discount_per_unit?: string;
  discount_amount?: string;
  discount_reason?: string | null;
  discount_source?: string;
  free_quantity?: string;
  chargeable_quantity?: string;
  accepted_quantity?: string;
  gross_amount?: string;
  taxable_amount?: string;
  net_line_amount?: string;
  effective_unit_cost?: string;
  landed_unit_cost?: string;
  allocated_invoice_discount?: string;
  promotion_id?: string | null;
  discount_rule_id?: string | null;
  discount_verified?: boolean;
  tax_amount: string;
  tax_rate: string;
  mrp?: string | null;
  selling_price?: string | null;
  line_total: string;
  confidence?: string | null;
  match_status: string;
  batch_number?: string | null;
  manufacturing_date?: string | null;
  expiry_date?: string | null;
  create_new_product?: boolean;
  variant_attributes?: Record<string, string>;
  classification_verified?: boolean;
  user_verified: boolean;
}

export interface Purchase {
  id: string;
  store_id?: string | null;
  supplier_id?: string | null;
  uploaded_file_id?: string | null;
  purchase_document_id?: string | null;
  processing_job_id?: string | null;
  invoice_number?: string | null;
  purchase_date: string;
  invoice_date?: string | null;
  received_date?: string | null;
  due_date?: string | null;
  supplier_name?: string | null;
  payment_mode: string;
  amount_paid: string;
  place_of_supply?: string | null;
  purchase_reference?: string | null;
  notes?: string | null;
  warehouse?: string | null;
  currency: string;
  status: PurchaseStatus;
  total_amount: string;
  subtotal: string;
  discount: string;
  invoice_discount_type?: "NONE" | "PERCENTAGE" | "FIXED_AMOUNT" | "TRADE_DISCOUNT" | "CASH_DISCOUNT" | "COUPON" | "PROMOTIONAL" | "MANUAL_ADJUSTMENT";
  invoice_discount_percentage?: string;
  invoice_discount_amount?: string;
  invoice_discount_reason?: string | null;
  invoice_discount_allocation_method?: "BY_ITEM_VALUE" | "BY_TAXABLE_VALUE" | "BY_QUANTITY" | "EQUALLY" | "MANUAL" | "DO_NOT_ALLOCATE";
  invoice_tax_rate: string;
  tax_amount: string;
  packaging_amount: string;
  freight_amount: string;
  round_off: string;
  image_hash?: string | null;
  ai_processing_status: string;
  workflow_status: string;
  version: number;
  total_quantity: number | string;
  balance_due: string;
  created_at: string;
  updated_at: string;
  confirmed_at?: string | null;
  items: PurchaseItem[];
}

export interface PurchaseDetail extends Purchase {
  supplier?: { id: string; name: string; gst_number?: string | null; address?: string | null; phone?: string | null; email?: string | null } | null;
  document?: { id: string; original_filename: string; content_type: string; file_size_bytes: number; sha256: string } | null;
  processing_job?: PurchaseDocumentJob | null;
  audit_history: Array<{ id: string; action: string; reason?: string | null; before_data?: Record<string, unknown> | null; after_data?: Record<string, unknown> | null; performed_by?: string | null; created_at: string }>;
}

export interface StockHistory {
  id: string;
  product_id: string;
  product_variant_id?: string | null;
  store_id?: string | null;
  movement_type: StockMovementType;
  qty: number;
  before_stock: number;
  after_stock: number;
  reference?: string | null;
  request_id?: string | null;
  correction_of_id?: string | null;
  correction_reason?: string | null;
  correction_notes?: string | null;
  movement_date: string;
  created_by?: string | null;
  product?: Pick<Product, "id" | "name" | "size" | "color" | "sku"> | null;
  created_by_user?: { id: string; full_name: string } | null;
}

export interface DashboardSummary {
  total_products: number;
  total_stock: number;
  low_stock_count: number;
  inventory_value: string;
  low_stock_products: Array<{
    id: string;
    name: string;
    size: string;
    color: string;
    current_stock: number;
    minimum_stock: number;
    brand_name: string;
    category_name: string;
  }>;
  recent_purchases: Purchase[];
  recent_stock_changes: StockHistory[];
  latest_products: Product[];
  stock_distribution: Array<{ label: string; value: number }>;
  category_distribution: Array<{ label: string; value: number }>;
  brand_distribution: Array<{ label: string; value: number }>;
  top_selling_products: Array<{ label: string; value: number }>;
}

export interface PurchaseUploadResponse {
  purchase: Purchase;
  extracted_invoice: {
    supplier?: string | null;
    invoice_number?: string | null;
    date?: string | null;
    total_amount: string;
    items: PurchaseItem[];
  };
  review_items: PurchaseItem[];
  duplicate_warning?: string | null;
}

export interface PurchaseDocumentAccepted {
  document_id: string;
  job_id: string;
  status: string;
  request_id: string;
  duplicate?: boolean;
}

export interface PurchaseDocumentJob {
  id: string;
  document_id: string;
  status: string;
  progress: number;
  message: string;
  request_id: string;
  provider_name: string;
  error_code?: string | null;
  error_message?: string | null;
  result?: { extracted_invoice: PurchaseUploadResponse["extracted_invoice"]; review_items: PurchaseItem[]; warnings: string[] } | null;
}

export interface Supplier {
  id: string;
  store_id?: string | null;
  name: string;
  contact_person?: string | null;
  phone?: string | null;
  alternate_phone?: string | null;
  email?: string | null;
  gst_number?: string | null;
  pan_number?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  opening_balance: string;
  credit_limit?: string | null;
  notes?: string | null;
  is_active: boolean;
  purchase_total: string;
  paid_total: string;
  balance_due: string;
  created_at: string;
  updated_at: string;
}

export interface SupplierDetail extends Supplier {
  payments: Array<{ id: string; supplier_id: string; payment_date?: string | null; amount: string; payment_mode: string; reference?: string | null; notes?: string | null; created_at: string }>;
  ledger: Array<{ id: string; entry_type: string; entry_date: string; reference?: string | null; description: string; debit: string; credit: string; balance: string }>;
}

export interface Customer {
  id: string;
  store_id: string;
  name: string;
  phone?: string | null;
  alternate_phone?: string | null;
  email?: string | null;
  gst_number?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  opening_credit: string;
  credit_limit?: string | null;
  notes?: string | null;
  is_active: boolean;
  credit_sales_total: string;
  paid_total: string;
  balance_due: string;
  created_at: string;
  updated_at: string;
}

export interface CustomerDetail extends Customer {
  payments: Array<{ id: string; customer_id: string; payment_date?: string | null; amount: string; payment_mode: string; reference?: string | null; notes?: string | null; created_at: string }>;
  ledger: Array<{ id: string; entry_type: string; entry_date: string; reference?: string | null; description: string; debit: string; credit: string; balance: string }>;
}

export interface ExpenseCategory {
  id: string;
  store_id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Expense {
  id: string;
  store_id: string;
  category_id: string;
  expense_date: string;
  title: string;
  vendor?: string | null;
  amount: string;
  payment_mode: string;
  reference?: string | null;
  notes?: string | null;
  receipt_url?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  category?: ExpenseCategory | null;
}

export interface ReportsSummary {
  has_report_data: boolean;
  profit_and_loss: {
    start_date: string;
    end_date: string;
    sales_total: string;
    purchase_total: string;
    expense_total: string;
    gross_profit: string;
    net_profit: string;
  };
  cash_flow: {
    start_date: string;
    end_date: string;
    cash_sales: string;
    supplier_payments: string;
    customer_payments: string;
    expenses: string;
    net_cash_flow: string;
  };
  inventory_valuation: {
    total_stock: number;
    purchase_value: string;
    selling_value: string;
    potential_margin: string;
  };
}

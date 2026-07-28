export type UserRole = "OWNER" | "MANAGER" | "STAFF";
export type PricingType = "MRP" | "OWN_PRICE";
export type PurchaseStatus = "DRAFT" | "REVIEWED" | "CONFIRMED" | "CANCELLED" | "VOIDED";
export type StockMovementType = "PURCHASE" | "SALE" | "CUSTOMER_RETURN" | "SUPPLIER_RETURN" | "DAMAGE" | "MANUAL_ADJUSTMENT" | "SALE_EDIT_RETURN" | "SALE_EDIT_DECREASE" | "SALE_VOID" | "PURCHASE_VOID";
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
  image_url?: string | null;
  is_active: boolean;
  is_test_data: boolean;
  category?: Category | null;
  subcategory?: SubCategory | null;
  brand?: Brand | null;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  color?: string | null;
  size?: string | null;
  created_at: string;
}

export interface SaleItem {
  id: string;
  product_id: string;
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
}

export interface Sale {
  id: string;
  invoice_number: string;
  customer_name?: string | null;
  payment_mode: string;
  subtotal: string;
  discount: string;
  total_amount: string;
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

export interface PaginatedProducts {
  items: Product[];
  meta: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export interface PurchaseItem {
  id?: string;
  product_id?: string | null;
  matched_product_id?: string | null;
  category_id?: string | null;
  brand_id?: string | null;
  brand_name?: string | null;
  category_name?: string | null;
  product_name: string;
  barcode?: string | null;
  supplier_product_code?: string | null;
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
  line_total: string;
  confidence?: string | null;
  match_status: string;
  batch_number?: string | null;
  expiry_date?: string | null;
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
  movement_type: StockMovementType;
  qty: number;
  before_stock: number;
  after_stock: number;
  reference?: string | null;
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
}

export interface PurchaseDocumentJob {
  id: string;
  document_id: string;
  status: string;
  progress: number;
  message: string;
  request_id: string;
  error_code?: string | null;
  error_message?: string | null;
  result?: { extracted_invoice: PurchaseUploadResponse["extracted_invoice"]; review_items: PurchaseItem[]; warnings: string[] } | null;
}

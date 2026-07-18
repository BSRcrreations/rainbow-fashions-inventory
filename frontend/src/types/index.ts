export type UserRole = "OWNER" | "MANAGER" | "STAFF";
export type PricingType = "MRP" | "OWN_PRICE";
export type PurchaseStatus = "DRAFT" | "REVIEWED" | "CONFIRMED" | "CANCELLED";
export type StockMovementType = "PURCHASE" | "SALE" | "CUSTOMER_RETURN" | "SUPPLIER_RETURN" | "DAMAGE" | "MANUAL_ADJUSTMENT";

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
  size: string;
  color: string;
  purchase_price: string;
  selling_price: string;
  pricing_type: PricingType;
  mrp?: string | null;
  current_stock: number;
  minimum_stock: number;
  barcode?: string | null;
  image_url?: string | null;
  is_active: boolean;
  category?: Category | null;
  subcategory?: SubCategory | null;
  brand?: Brand | null;
}

export interface SaleItem {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  unit_cost: string;
  line_total: string;
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
  sale_date: string;
  cashier?: { id: string; full_name: string } | null;
  items: SaleItem[];
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
  size: string;
  color: string;
  quantity: number;
  purchase_price: string;
  mrp?: string | null;
  line_total: string;
  confidence?: string | null;
}

export interface Purchase {
  id: string;
  invoice_number?: string | null;
  invoice_date?: string | null;
  supplier_name?: string | null;
  status: PurchaseStatus;
  total_amount: string;
  created_at: string;
  confirmed_at?: string | null;
  items: PurchaseItem[];
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
}

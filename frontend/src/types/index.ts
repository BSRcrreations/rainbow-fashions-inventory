export type UserRole = "OWNER" | "MANAGER" | "STAFF";
export type PricingType = "MRP" | "OWN_PRICE";
export type PurchaseStatus = "DRAFT" | "REVIEWED" | "CONFIRMED" | "CANCELLED";
export type StockMovementType = "PURCHASE" | "SALE" | "ADJUSTMENT";

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
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  category_id: string;
  brand_id: string;
  name: string;
  size: string;
  color: string;
  purchase_price: string;
  selling_price: string;
  pricing_type: PricingType;
  mrp?: string | null;
  gst_rate?: string | null;
  hsn_code?: string | null;
  current_stock: number;
  minimum_stock: number;
  barcode?: string | null;
  image_url?: string | null;
  is_active: boolean;
  category?: Category | null;
  brand?: Brand | null;
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

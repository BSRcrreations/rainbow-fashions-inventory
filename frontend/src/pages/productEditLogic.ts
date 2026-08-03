import type { PricingType, Product } from "../types";

export interface ProductEditFormState {
  category_id: string;
  subcategory_id: string;
  brand_id: string;
  sku: string;
  name: string;
  has_sizes: boolean;
  sizes: string[];
  has_colors: boolean;
  colors: string[];
  purchase_price: string;
  selling_price: string;
  pricing_type: PricingType;
  mrp: string;
  current_stock: string;
  minimum_stock: string;
  barcode: string;
  product_date: string;
  description: string;
  hsn_sac: string;
  is_active: boolean;
  is_test_data: boolean;
}

function normalizedValues(values: string[], enabled: boolean) {
  return enabled ? values.map((value) => value.trim()).filter(Boolean) : [];
}

function sameValues(left: string[], right: string[]) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function originalVariantValues(product: Product) {
  const variants = product.variants ?? [];
  return {
    sizes: Array.from(new Set(variants.map((variant) => variant.size).filter((value): value is string => Boolean(value)))),
    colors: Array.from(new Set(variants.map((variant) => variant.color).filter((value): value is string => Boolean(value)))),
  };
}

export function productPayload(form: ProductEditFormState, editing?: Product | null) {
  const sizes = normalizedValues(form.sizes, form.has_sizes);
  const colors = normalizedValues(form.colors, form.has_colors);
  const payload = {
    category_id: form.category_id,
    subcategory_id: form.subcategory_id,
    brand_id: form.brand_id,
    sku: form.sku.trim() || null,
    name: form.name.trim(),
    purchase_price: Number(form.purchase_price),
    selling_price: Number(form.selling_price),
    mrp: form.mrp ? Number(form.mrp) : null,
    minimum_stock: Number(form.minimum_stock),
    barcode: form.barcode.trim() || null,
    product_date: form.product_date,
    description: form.description.trim() || null,
    hsn_sac: form.hsn_sac.trim() || null,
    is_active: form.is_active,
    is_test_data: form.is_test_data,
    pricing_type: form.pricing_type,
  };

  if (!editing) {
    return { ...payload, current_stock: Number(form.current_stock), size: sizes[0] ?? null, color: colors[0] ?? null, sizes, colors };
  }

  const original = originalVariantValues(editing);
  if (!sameValues(sizes, original.sizes) || !sameValues(colors, original.colors)) {
    return { ...payload, sizes, colors };
  }
  return payload;
}

export function productUpdateErrorMessage(code?: string, fallback?: string) {
  const messages: Record<string, string> = {
    PRODUCT_NAME_REQUIRED: "Enter a product name.",
    PRODUCT_ALREADY_EXISTS: "A product with this name and brand already exists.",
    BARCODE_ALREADY_ASSIGNED: "This barcode is already assigned to another variant.",
    VARIANT_ALREADY_EXISTS: "This size and colour variant already exists.",
    STOCK_FIELDS_READ_ONLY: "Current stock cannot be edited directly. Use Stock Adjustment.",
    PRODUCT_UPDATE_FAILED: "The product could not be updated.",
  };
  return code && messages[code] ? messages[code] : fallback || "The product could not be updated.";
}

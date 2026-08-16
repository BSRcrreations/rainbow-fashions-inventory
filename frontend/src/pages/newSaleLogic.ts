import type { ProductVariantBarcode, SaleCatalogProduct, SaleCatalogVariant } from "../types";

export interface CartLine {
  product: SaleCatalogProduct;
  variant: SaleCatalogVariant;
  quantity: number;
}

function variantLabel(variant: SaleCatalogVariant) {
  return [variant.size, variant.color, variant.style_code].filter(Boolean).join(" · ") || variant.sku;
}

export function firstSellableProduct(products: SaleCatalogProduct[]) {
  return products.find((product) => product.variants.some((variant) => variant.is_active && variant.available_stock > 0));
}

export function isQuickAddProduct(product: SaleCatalogProduct) {
  return product.variants.filter((variant) => variant.is_active && variant.available_stock > 0).length === 1;
}

export function mergeCartVariant(cart: CartLine[], product: SaleCatalogProduct, variant: SaleCatalogVariant, quantityToAdd = 1) {
  if (!variant.is_active || variant.available_stock <= 0) return { cart, error: `${product.name} (${variantLabel(variant)}) is out of stock` };
  const existing = cart.find((line) => line.variant.variant_id === variant.variant_id);
  if (existing && existing.quantity + quantityToAdd > variant.available_stock) return { cart, error: `Only ${variant.available_stock} units available` };
  if (!existing && quantityToAdd > variant.available_stock) return { cart, error: `Only ${variant.available_stock} units available` };
  return { cart: existing ? cart.map((line) => line.variant.variant_id === variant.variant_id ? { ...line, quantity: line.quantity + quantityToAdd } : line) : [...cart, { product, variant, quantity: quantityToAdd }] };
}

/** A visual catalog group can contain same-named products; retain the variant's true parent in the cart. */
export function productForVariant(product: SaleCatalogProduct, variant: SaleCatalogVariant): SaleCatalogProduct {
  return product.product_id === variant.product_id ? product : { ...product, product_id: variant.product_id, variants: [variant], variant_count: 1, total_stock: variant.available_stock, total_available_stock: variant.available_stock };
}

export function catalogItemFromBarcode(found: ProductVariantBarcode): { product: SaleCatalogProduct; variant: SaleCatalogVariant } {
  const variant: SaleCatalogVariant = { variant_id: found.variant_id, product_id: found.product_id, size: found.size, color: found.color, style_code: found.style_code, sku: found.sku, barcode: found.barcode, mrp: found.mrp, selling_price: found.selling_price, available_stock: found.current_available_stock, classification_review_required: false, is_active: found.active, scan_unit: found.scan_unit === "PACK" ? "PACK" : "PIECE", pieces_per_pack: found.base_unit_conversion };
  return { variant, product: { product_id: found.product_id, name: found.product_name, category_name: found.category, brand_name: found.brand, variant_count: 1, total_stock: found.current_available_stock, minimum_stock: 0, total_available_stock: found.current_available_stock, variants: [variant] } };
}

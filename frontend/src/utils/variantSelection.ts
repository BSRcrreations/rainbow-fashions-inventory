import { api } from "../api/client";
import type { SaleCatalogProduct, SaleCatalogVariant } from "../types";
import type { SharedTarget } from "../components/VariantPicker";
export async function resolveSharedVariant(target: SharedTarget): Promise<{ product: SaleCatalogProduct; variant: SaleCatalogVariant }> {
  const variant = await api.get<SaleCatalogVariant>(`/sales/catalog/variant/${target.variant_id}`);
  return { variant, product: { product_id: variant.product_id, name: target.product_name, brand_name: target.brand_name, variant_count: 1, total_stock: variant.available_stock, total_available_stock: variant.available_stock, minimum_stock: 0, variants: [variant] } };
}

import type { SaleCatalogProduct } from "../types";
import { money } from "../utils/format";

function compactParts(parts: Array<string | null | undefined>) {
  return parts.map((part) => part?.trim()).filter((part): part is string => Boolean(part));
}

export function previewVariant(product: SaleCatalogProduct) {
  return product.variants.find((variant) => variant.is_active && variant.available_stock > 0) ?? product.variants.find((variant) => variant.is_active) ?? product.variants[0] ?? null;
}

export function productCardVariantSummary(product: SaleCatalogProduct) {
  const variant = previewVariant(product);
  if (!variant) return "";
  return compactParts([variant.size, variant.color, variant.style_code]).join(" • ") || variant.sku;
}

export function productCardMrpText(product: SaleCatalogProduct) {
  const mrps = product.variants.flatMap((variant) => {
    if (!variant.mrp) return [];
    const value = Number(variant.mrp);
    return Number.isFinite(value) ? [value] : [];
  });
  if (!mrps.length) return "MRP -";
  const uniqueMrps = Array.from(new Set(mrps));
  const amount = uniqueMrps.length > 1 ? Math.min(...mrps) : mrps[0];
  return `${uniqueMrps.length > 1 ? "From" : "MRP"} ${money(amount)}`;
}

export function categoryBrandLine(categoryName?: string | null, brandName?: string | null) {
  return compactParts([categoryName || "Uncategorised", brandName]).join(" · ");
}

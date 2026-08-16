import type { SaleCatalogProduct, SaleCatalogVariant } from "../types";
import { money } from "../utils/format";

const logicalSizeOrder = ["XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "FREE SIZE"];

function normalizedSize(size?: string | null) {
  return (size || "").trim().replace(/\s+/g, " ").toUpperCase();
}

/** Keeps POS size choices in customer-facing order while retaining unknown labels. */
export function orderVariantsBySize(variants: SaleCatalogVariant[]) {
  return variants.map((variant, index) => ({ variant, index })).sort((left, right) => {
    const leftIndex = logicalSizeOrder.indexOf(normalizedSize(left.variant.size));
    const rightIndex = logicalSizeOrder.indexOf(normalizedSize(right.variant.size));
    const leftKnown = leftIndex !== -1;
    const rightKnown = rightIndex !== -1;
    if (leftKnown && rightKnown) return leftIndex - rightIndex || left.index - right.index;
    if (leftKnown) return -1;
    if (rightKnown) return 1;
    return left.index - right.index;
  }).map(({ variant }) => variant);
}

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

import type { Product } from "../types";

export function productVariantLabel(product: Pick<Product, "variants" | "size" | "color">) {
  const variants = product.variants ?? [];
  const sizes = Array.from(new Set(variants.map((variant) => variant.size).filter((value): value is string => Boolean(value))));
  const colors = Array.from(new Set(variants.map((variant) => variant.color).filter((value): value is string => Boolean(value))));
  if (!sizes.length && product.size) sizes.push(product.size);
  if (!colors.length && product.color) colors.push(product.color);
  return [sizes.length ? `Sizes: ${sizes.join(", ")}` : "", colors.length ? `Colors: ${colors.join(", ")}` : ""].filter(Boolean).join(" · ") || "No variants";
}

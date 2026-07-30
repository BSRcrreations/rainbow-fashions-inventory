import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ProductVisual } from "./NewSalePage";
import { catalogItemFromBarcode, firstSellableProduct, isQuickAddProduct, mergeCartVariant } from "./newSaleLogic";
import type { ProductVariantBarcode, SaleCatalogProduct, SaleCatalogVariant } from "../types";

const baseProduct: SaleCatalogProduct = {
  product_id: "prisma-leggings",
  name: "Full Leggings",
  brand_name: "Prisma",
  category_name: "Leggings",
  variant_count: 1,
  total_stock: 10,
  total_available_stock: 10,
  minimum_stock: 2,
  variants: [],
};

describe("ProductVisual", () => {
  it("prefers the brand logo over the product image", () => {
    const markup = renderToStaticMarkup(<ProductVisual product={{ ...baseProduct, brand_logo_url: "/uploads/products/prisma.webp", product_image_url: "/uploads/products/leggings.jpg" }} />);

    expect(markup).toContain('src="/uploads/products/prisma.webp"');
    expect(markup).not.toContain('src="/uploads/products/leggings.jpg"');
  });

  it("falls back to the product image and then brand initials", () => {
    const productImageMarkup = renderToStaticMarkup(<ProductVisual product={{ ...baseProduct, product_image_url: "/uploads/products/leggings.jpg" }} />);
    const initialsMarkup = renderToStaticMarkup(<ProductVisual product={baseProduct} />);

    expect(productImageMarkup).toContain('src="/uploads/products/leggings.jpg"');
    expect(initialsMarkup).toContain(">P<");
  });
});

const smallVariant: SaleCatalogVariant = { variant_id: "variant-small", size: "S", color: "Black", sku: "LEG-S", barcode: "8901", selling_price: "499", available_stock: 2, classification_review_required: false, is_active: true };
const largeVariant: SaleCatalogVariant = { ...smallVariant, variant_id: "variant-large", size: "L", barcode: "8902" };

describe("New Sale cart behavior", () => {
  it("merges the same exact variant but keeps sizes and colours as separate lines", () => {
    const first = mergeCartVariant([], { ...baseProduct, variants: [smallVariant, largeVariant] }, smallVariant);
    const merged = mergeCartVariant(first.cart, baseProduct, smallVariant);
    const separate = mergeCartVariant(merged.cart, baseProduct, largeVariant);

    expect(merged.cart).toHaveLength(1);
    expect(merged.cart[0].quantity).toBe(2);
    expect(separate.cart).toHaveLength(2);
  });

  it("does not allow a cart quantity above current store stock", () => {
    const result = mergeCartVariant([{ product: baseProduct, variant: smallVariant, quantity: 2 }], baseProduct, smallVariant);

    expect(result.cart[0].quantity).toBe(2);
    expect(result.error).toBe("Only 2 units available");
  });

  it("finds the first sellable result and only quick-adds a single available variant", () => {
    const unavailable = { ...baseProduct, product_id: "sold-out", variants: [{ ...smallVariant, available_stock: 0 }] };
    const single = { ...baseProduct, variants: [smallVariant, { ...largeVariant, available_stock: 0 }] };
    const multiple = { ...baseProduct, variants: [smallVariant, largeVariant] };

    expect(firstSellableProduct([unavailable, single])).toBe(single);
    expect(isQuickAddProduct(single)).toBe(true);
    expect(isQuickAddProduct(multiple)).toBe(false);
  });

  it("maps an exact barcode response to its exact variant", () => {
    const barcode: ProductVariantBarcode = { product_id: "product-1", variant_id: "variant-blue-large", product_name: "Full Leggings", category: "Leggings", brand: "Prisma", size: "L", color: "Blue", sku: "PRISMA-L-BLU", barcode: "890123", selling_price: "549", current_physical_stock: 4, current_available_stock: 4, active: true, package_quantity: 1, scan_unit: "PIECE", inventory_unit: "PIECE", base_unit_conversion: 1, sale_mode: "PIECE_ONLY" };
    const result = catalogItemFromBarcode(barcode);

    expect(result.variant.variant_id).toBe("variant-blue-large");
    expect(result.product.variants).toEqual([result.variant]);
  });
});

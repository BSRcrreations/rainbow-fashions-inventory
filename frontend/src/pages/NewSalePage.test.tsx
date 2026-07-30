import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ProductVisual } from "./NewSalePage";
import type { SaleCatalogProduct } from "../types";

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

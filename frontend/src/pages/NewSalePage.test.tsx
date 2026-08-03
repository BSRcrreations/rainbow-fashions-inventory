import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CurrentSalePanel, ProductGroupCard, ProductVisual } from "./NewSalePage";
import { productCardMrpText, productCardVariantSummary } from "./newSaleCard";
import { catalogItemFromBarcode, firstSellableProduct, isQuickAddProduct, mergeCartVariant } from "./newSaleLogic";
import type { CartLine } from "./newSaleLogic";
import { previewSaleDiscount } from "./saleDiscount";
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

function renderProductCard(product: SaleCatalogProduct) {
  return renderToStaticMarkup(<ProductGroupCard product={product} selected={false} onChoose={() => undefined} />);
}

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

describe("New Sale product cards", () => {
  it("shows product name, category, brand, variant preview, MRP, count, and stock", () => {
    const product: SaleCatalogProduct = {
      ...baseProduct,
      product_id: "soft-padded-bra",
      name: "Soft padded bra",
      category_name: "Bra",
      brand_name: "withIn",
      total_stock: 30,
      total_available_stock: 30,
      variant_count: 1,
      variants: [{ ...smallVariant, size: "34/85 cm", color: "all", style_code: "SoftA", sku: "SOFTA-34", mrp: "395", selling_price: "395", available_stock: 30 }],
    };

    const markup = renderProductCard(product);

    expect(markup).toContain("Soft padded bra");
    expect(markup).toContain("Bra · withIn");
    expect(markup).toContain("34/85 cm • all • SoftA");
    expect(markup).toContain("MRP ₹395.00");
    expect(markup).toContain("1 variant");
    expect(markup).toContain("30 in stock");
  });

  it("uses the first sellable variant as the compact multiple-variant preview", () => {
    const product = {
      ...baseProduct,
      variant_count: 2,
      total_stock: 11,
      total_available_stock: 11,
      variants: [
        { ...smallVariant, variant_id: "sold-out", size: "S", color: "Black", style_code: "SoftA", mrp: "395", available_stock: 0 },
        { ...largeVariant, variant_id: "sellable", size: "L", color: "Blue", style_code: "SoftB", mrp: "425", selling_price: "425", available_stock: 11 },
      ],
    };

    const markup = renderProductCard(product);

    expect(markup).toContain("Preview: L • Blue • SoftB");
    expect(markup).toContain("2 variants");
    expect(markup).toContain("11 in stock");
  });

  it("does not render broken separators when size, colour, or variant name is missing", () => {
    const product = { ...baseProduct, variants: [{ ...smallVariant, size: "34/85 cm", color: "", style_code: "SoftA", mrp: "395" }] };

    expect(productCardVariantSummary(product)).toBe("34/85 cm • SoftA");
    expect(productCardVariantSummary({ ...baseProduct, variants: [{ ...smallVariant, size: "", color: "all", style_code: "" }] })).toBe("all");
    expect(productCardVariantSummary({ ...baseProduct, variants: [{ ...smallVariant, size: "", color: "", style_code: "" }] })).toBe("LEG-S");
    expect(renderProductCard(product)).not.toContain("· ·");
  });

  it("shows an MRP range when multiple variant MRPs differ", () => {
    const product = { ...baseProduct, variants: [{ ...smallVariant, mrp: "499" }, { ...largeVariant, mrp: "549" }] };

    expect(productCardMrpText(product)).toBe("From ₹499.00");
  });

  it("keeps long product and variant text constrained inside the card", () => {
    const product = {
      ...baseProduct,
      name: "Very Long Soft Padded Bra Name For Billing Counter Search",
      category_name: "Very Long Category Name",
      brand_name: "Very Long Brand Name",
      variants: [{ ...smallVariant, size: "34/85 cm extra long size", color: "assorted colour family", style_code: "SoftA ultra comfort padded long label", mrp: "395" }],
    };

    const markup = renderProductCard(product);

    expect(markup).toContain("truncate");
    expect(markup).toContain("max-h-10");
    expect(markup).toContain("Very Long Soft Padded Bra Name");
    expect(markup).toContain("34/85 cm extra long size • assorted colour family • SoftA ultra comfort padded long label");
  });

  it("still renders the card as a product-selection button for the variant popup", () => {
    const markup = renderProductCard({ ...baseProduct, variants: [smallVariant] });

    expect(markup.startsWith("<button")).toBe(true);
    expect(markup).toContain('type="button"');
    expect(markup).toContain('aria-pressed="false"');
  });
});

const cartLine: CartLine = {
  product: { ...baseProduct, name: "Softa Padded Bra", brand_name: "WithIn", category_name: "Bras" },
  variant: { ...smallVariant, variant_id: "softa-34", size: "34", color: "Assorted", sku: "SOFTA-34", barcode: "8906000000001", mrp: "395", selling_price: "395", available_stock: 8 },
  quantity: 3,
};

function renderCart(cart: CartLine[]) {
  const subtotal = cart.reduce((total, line) => total + Number(line.variant.selling_price) * line.quantity, 0);
  return renderToStaticMarkup(<CurrentSalePanel
    cart={cart}
    customerName=""
    paymentMode="CASH"
    discountType="PERCENTAGE"
    discountValue="10"
    subtotal={subtotal}
    preview={previewSaleDiscount(subtotal, "PERCENTAGE", "10")}
    pending={false}
    onCustomer={() => undefined}
    onPayment={() => undefined}
    onDiscountType={() => undefined}
    onDiscountValue={() => undefined}
    onChangeQuantity={() => undefined}
    onSetQuantity={() => undefined}
    onRemove={() => undefined}
    onClear={() => undefined}
    onSubmit={(event) => event.preventDefault()}
  />);
}

describe("Current Sale cart panel", () => {
  it("shows the empty state only when the cart has no lines", () => {
    const markup = renderCart([]);

    expect(markup).toContain("Your cart is empty");
    expect(markup).not.toContain("Softa Padded Bra");
  });

  it("renders the cart line before customer, payment, discount, and totals", () => {
    const markup = renderCart([cartLine]);

    expect(markup).not.toContain("Your cart is empty");
    expect(markup).toContain('data-testid="cart-item-list"');
    expect(markup).toContain("min-h-[148px]");
    expect(markup).toContain("max-h-[40svh]");
    expect(markup).toContain("overflow-y-auto");
    expect(markup).toContain("Softa Padded Bra");
    expect(markup).toContain("Brand: WithIn");
    expect(markup).toContain("Bras · Size: 34 · Colour: Assorted");
    expect(markup).toContain("Barcode: 8906000000001");
    expect(markup).toContain("MRP ₹395.00 · ₹395.00 × 3");
    expect(markup).toContain("Available stock: 8 · Stock after sale: 5");
    expect(markup).toContain("₹1,185.00");
    expect(markup).toContain("1 line · 3 units");
    expect(markup).toContain("Decrease Softa Padded Bra");
    expect(markup).toContain("Increase Softa Padded Bra");
    expect(markup).toContain(">Remove<");
    expect(markup.indexOf("Softa Padded Bra")).toBeLessThan(markup.indexOf("Customer"));
    expect(markup.indexOf("Customer")).toBeLessThan(markup.indexOf("Payment method"));
    expect(markup.indexOf("Payment method")).toBeLessThan(markup.indexOf("Discount type"));
    expect(markup.indexOf("Discount type")).toBeLessThan(markup.indexOf("Subtotal"));
  });
});

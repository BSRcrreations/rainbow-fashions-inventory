import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CompactCartPreview, CurrentSalePanel, ProductGroupCard, ProductVisual } from "./NewSalePage";
import { orderVariantsBySize, productCardMrpText, productCardVariantSummary } from "./newSaleCard";
import { catalogItemFromBarcode, firstSellableProduct, isQuickAddProduct, mergeCartVariant, productForVariant } from "./newSaleLogic";
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

const smallVariant: SaleCatalogVariant = { variant_id: "variant-small", product_id: "prisma-leggings", size: "S", color: "Black", sku: "LEG-S", barcode: "8901", selling_price: "499", available_stock: 2, classification_review_required: false, is_active: true };
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
    expect(result.variant.product_id).toBe("product-1");
    expect(result.product.variants).toEqual([result.variant]);
  });

  it("retains the pack conversion on a barcode-selected cart variant", () => {
    const barcode: ProductVariantBarcode = { product_id: "product-1", variant_id: "variant-pack", product_name: "Pack leggings", category: "Leggings", brand: "Prisma", size: "L", color: "Blue", sku: "PACK-L", barcode: "890124", selling_price: "549", current_physical_stock: 12, current_available_stock: 12, active: true, package_quantity: 6, scan_unit: "PACK", inventory_unit: "PIECE", base_unit_conversion: 6, sale_mode: "PACK_ONLY" };
    const result = catalogItemFromBarcode(barcode);
    expect(result.variant.scan_unit).toBe("PACK");
    expect(result.variant.pieces_per_pack).toBe(6);
    expect(mergeCartVariant([], result.product, result.variant, barcode.package_quantity).cart[0].quantity).toBe(6);
  });

  it("keeps the exact parent product identity when a visual catalog group contains matching products", () => {
    const exactVariant = { ...largeVariant, product_id: "separate-product" };

    expect(productForVariant(baseProduct, exactVariant).product_id).toBe("separate-product");
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
    expect(markup).toContain("Select size");
    expect(markup).toContain("34/85 cm");
    expect(markup).toContain("MRP ₹395.00");
    expect(markup).toContain("1 variant");
    expect(markup).toContain("30 in stock");
  });

  it("renders logical, contained size chips for multiple variants", () => {
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

    expect(markup).toContain("Select size");
    expect(markup).toContain('data-testid="size-chips-prisma-leggings"');
    expect(markup).toContain("flex flex-wrap");
    expect(markup).toContain("S");
    expect(markup).toContain("L");
    expect(markup).toContain("2 variants");
    expect(markup).toContain("11 in stock");
  });

  it("orders known sizes logically and leaves custom sizes after them", () => {
    const variants = orderVariantsBySize([
      { ...smallVariant, variant_id: "custom", size: "One Size" },
      { ...smallVariant, variant_id: "xl", size: "XL" },
      { ...smallVariant, variant_id: "small", size: "S" },
      { ...smallVariant, variant_id: "free", size: "Free Size" },
      { ...smallVariant, variant_id: "medium", size: "M" },
    ]);

    expect(variants.map((variant) => variant.size)).toEqual(["S", "M", "XL", "Free Size", "One Size"]);
  });

  it("keeps unavailable sizes visible but disabled", () => {
    const markup = renderProductCard({ ...baseProduct, variant_count: 2, variants: [smallVariant, { ...largeVariant, available_stock: 0 }] });

    expect(markup).toContain('disabled=""');
    expect(markup).toContain("line-through");
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
    expect(markup).toContain("34/85 cm extra long size");
    expect(markup).toContain("flex flex-wrap");
  });

  it("keeps a product selection control without nesting the size buttons", () => {
    const markup = renderProductCard({ ...baseProduct, variants: [smallVariant] });

    expect(markup.startsWith("<article")).toBe(true);
    expect(markup).toContain('type="button"');
    expect(markup).toContain('aria-pressed="false"');
  });
});

const cartLine: CartLine = {
  product: { ...baseProduct, name: "Softa Padded Bra", brand_name: "WithIn", category_name: "Bras" },
  variant: { ...smallVariant, variant_id: "softa-34", size: "34", color: "Assorted", sku: "SOFTA-34", barcode: "8906000000001", mrp: "395", selling_price: "395", available_stock: 8 },
  quantity: 3,
};

function renderCart(cart: CartLine[], discountType: "NONE" | "PERCENTAGE" | "FIXED_AMOUNT" = "PERCENTAGE", discountValue = "10") {
  const subtotal = cart.reduce((total, line) => total + Number(line.variant.selling_price) * line.quantity, 0);
  const previewType = discountType === "NONE" ? "PERCENTAGE" : discountType;
  return renderToStaticMarkup(<CurrentSalePanel
    cart={cart}
    customerName=""
    paymentMode="CASH"
    discountType={discountType}
    discountValue={discountValue}
    subtotal={subtotal}
    preview={previewSaleDiscount(subtotal, previewType, discountType === "NONE" ? "0" : discountValue)}
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

function renderCompactCart(cart: CartLine[]) {
  return renderToStaticMarkup(<CompactCartPreview cart={cart} onCheckout={() => undefined} onChangeQuantity={() => undefined} onRemove={() => undefined} onClear={() => undefined} />);
}

describe("Compact sale cart", () => {
  it("keeps every cart line editable before checkout", () => {
    const secondLine = { ...cartLine, product: { ...cartLine.product, name: "Flexi Kurthi Pant" }, variant: { ...cartLine.variant, variant_id: "flexi-medium", size: "M", selling_price: "599", available_stock: 3 }, quantity: 2 };
    const markup = renderCompactCart([cartLine, secondLine]);

    expect(markup).toContain('data-testid="compact-cart-line-softa-34"');
    expect(markup).toContain('data-testid="compact-cart-line-flexi-medium"');
    expect(markup).toContain("Softa Padded Bra");
    expect(markup).toContain("Size: 34");
    expect(markup).toContain("Flexi Kurthi Pant");
    expect(markup).toContain("M");
    expect(markup).toContain("₹599.00");
    expect(markup).toContain("₹1,198.00");
    expect(markup).toContain("Increase Flexi Kurthi Pant in cart");
    expect(markup).toContain("Decrease Flexi Kurthi Pant in cart");
    expect(markup).toContain("Remove Flexi Kurthi Pant from cart");
    expect(markup).toContain("Clear Cart");
    expect(markup).toContain("Checkout");
  });
});

describe("Current Sale cart panel", () => {
  it("shows the empty state only when the cart has no lines", () => {
    const markup = renderCart([]);

    expect(markup).toContain("Your cart is empty");
    expect(markup).not.toContain("Softa Padded Bra");
  });

  it("renders the checkout review with cart items on the left and one payment action", () => {
    const markup = renderCart([cartLine]);

    expect(markup).not.toContain("Your cart is empty");
    expect(markup).toContain('data-testid="cart-item-list"');
    expect(markup).toContain("min-h-0");
    expect(markup).toContain("flex-1");
    expect(markup).toContain("overflow-y-auto");
    expect(markup).toContain("Softa Padded Bra");
    expect(markup).toContain("Brand: WithIn");
    expect(markup).toContain("Bras · Size: 34 · Colour: Assorted");
    expect(markup).toContain("Barcode: 8906000000001");
    expect(markup).toContain("MRP ₹395.00 · ₹395.00 × 3");
    expect(markup).toContain("Available stock: 8 · Stock after sale: 5");
    expect(markup).toContain("₹1,185.00");
    expect(markup).toContain("Product lines");
    expect(markup).toContain("Total units");
    expect(markup).toContain("Cart subtotal");
    expect(markup).toContain("Decrease Softa Padded Bra");
    expect(markup).toContain("Increase Softa Padded Bra");
    expect(markup).toContain('aria-label="Remove Softa Padded Bra"');
    expect(markup.indexOf("Softa Padded Bra")).toBeLessThan(markup.indexOf("Customer"));
    expect(markup.indexOf("Customer")).toBeLessThan(markup.indexOf("Payment"));
    expect(markup.indexOf("Payment")).toBeLessThan(markup.indexOf("Discount type"));
    expect(markup.indexOf("Discount type")).toBeLessThan(markup.indexOf("Subtotal"));
    expect(markup).toContain('data-testid="checkout-footer"');
    expect(markup).toContain("sticky bottom-0");
    expect(markup).toContain("Grand Total");
    expect(markup).toContain("Confirm Sale");
    expect(markup).toContain("Phone number");
    expect(markup).toContain("Address / Notes");
    expect(markup).toContain("Cash");
    expect(markup).toContain("UPI");
    expect(markup).not.toContain(">Card<");
    expect(markup).not.toContain(">Bank<");
    expect(markup).not.toContain("Save Bill");
    expect(markup).not.toContain("Save &amp; Print Bill");
  });

  it("hides irrelevant discount inputs when no discount is selected", () => {
    const markup = renderCart([cartLine], "NONE", "0");

    expect(markup).toContain('<option value="NONE" selected="">None</option>');
    expect(markup).not.toContain("Discount value");
    expect(markup).not.toContain(">5%<");
    expect(markup).not.toContain(">10%<");
  });
});

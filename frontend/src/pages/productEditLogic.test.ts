import { describe, expect, it } from "vitest";
import type { Product } from "../types";
import { productPayload, productUpdateErrorMessage } from "./productEditLogic";

const product: Product = {
  id: "product-1", category_id: "category-1", subcategory_id: "subcategory-1", brand_id: "brand-1", name: "Softa padded bra", sku: "SOFTA-34", barcode: "8906000000001", purchase_price: "220", selling_price: "395", pricing_type: "OWN_PRICE", mrp: "395", current_stock: 25, minimum_stock: 3, product_date: "2026-08-03", description: null, hsn_sac: null, image_url: null, is_active: true, is_test_data: false,
  variants: [{ id: "variant-34", product_id: "product-1", store_id: "store-1", size: "34", color: "Assorted", internal_sku: "SOFTA-34", barcode: "8906000000001", identity_key: "softa", mrp: "395", selling_price: "395", last_purchase_cost: "220", average_cost: "220", current_stock: 25, classification_review_required: false, is_active: true, created_at: "2026-08-03T00:00:00Z", updated_at: "2026-08-03T00:00:00Z" }],
};

const form = {
  category_id: "category-1", subcategory_id: "subcategory-1", brand_id: "brand-1", sku: "SOFTA-34", name: "  Soft padded bra  ", has_sizes: true, sizes: ["34"], has_colors: true, colors: ["Assorted"], purchase_price: "220", selling_price: "395", pricing_type: "OWN_PRICE" as const, mrp: "395", current_stock: "25", minimum_stock: "3", barcode: "8906000000001", product_date: "2026-08-03", description: "", hsn_sac: "", is_active: true, is_test_data: false,
};

describe("product edit payload", () => {
  it("renames a stocked product without sending stock or unchanged variant arrays", () => {
    const payload = productPayload(form, product);

    expect(payload).toMatchObject({ name: "Soft padded bra", selling_price: 395, minimum_stock: 3 });
    expect(payload).not.toHaveProperty("current_stock");
    expect(payload).not.toHaveProperty("sizes");
    expect(payload).not.toHaveProperty("colors");
  });

  it("keeps opening stock in create payloads only", () => {
    const payload = productPayload({ ...form, name: "Softa padded bra" });

    expect(payload).toMatchObject({ current_stock: 25, sizes: ["34"], colors: ["Assorted"] });
  });

  it("uses actionable structured update errors", () => {
    expect(productUpdateErrorMessage("PRODUCT_ALREADY_EXISTS")).toBe("A product with this name and brand already exists.");
    expect(productUpdateErrorMessage("BARCODE_ALREADY_ASSIGNED")).toBe("This barcode is already assigned to another variant.");
    expect(productUpdateErrorMessage("STOCK_FIELDS_READ_ONLY")).toContain("transaction-controlled");
    expect(productUpdateErrorMessage(undefined, "category_id: Input should be a valid UUID")).toBe("Select a category.");
  });

  it("normalizes optional IDs, barcodes, and decimal fields before submitting", () => {
    const payload = productPayload({ ...form, category_id: " ", subcategory_id: "", brand_id: "brand-1", barcode: "  000123  ", mrp: "" });

    expect(payload).toMatchObject({
      category_id: null,
      subcategory_id: null,
      brand_id: "brand-1",
      barcode: "000123",
      mrp: null,
      purchase_price: 220,
      selling_price: 395,
    });
  });
});

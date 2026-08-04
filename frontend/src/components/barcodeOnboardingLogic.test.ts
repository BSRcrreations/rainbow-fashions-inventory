import { describe, expect, it } from "vitest";
import {
  type BarcodeOnboardingFormState,
  barcodeOnboardingErrorMessage,
  existingVariantBarcodePayload,
  newProductBarcodePayload,
  newVariantBarcodePayload,
  validateBarcodeOnboarding,
} from "./barcodeOnboardingLogic";

const form: BarcodeOnboardingFormState = {
  product_name: "Padded Bra",
  category_id: "category-1",
  subcategory_id: "",
  brand_id: "brand-1",
  product_code: "",
  style_code: "SoftA",
  manufacturer_sku: "",
  internal_sku: "",
  size: "34/85 cm",
  color: "all",
  hsn_sac: "",
  quantity: "2",
  package_quantity: "1",
  scan_unit: "PIECE",
  inventory_unit: "PIECE",
  sale_mode: "PIECE_ONLY",
  purchase_cost: "250",
  mrp: "395",
  selling_price: "395",
  pricing_type: "MRP",
  product_date: "",
  minimum_stock: "0",
  description: "",
  alternate_barcode: "",
  package_barcode: "",
  package_barcode_quantity: "1",
  image_url: "",
};

describe("existingVariantBarcodePayload", () => {
  it("sends only the authoritative existing-variant assignment fields", () => {
    expect(existingVariantBarcodePayload("session-1", "0012345678905", "variant-1", 2)).toEqual({
      session_id: "session-1",
      action: "EXISTING_VARIANT",
      barcode: "0012345678905",
      product_variant_id: "variant-1",
      quantity: 2,
    });
  });

  it("preserves leading zeros in scanned barcodes", () => {
    expect(existingVariantBarcodePayload("session-1", "0000456", "variant-1", 1).barcode).toBe("0000456");
  });

  it("does not include prices or product metadata", () => {
    const payload = existingVariantBarcodePayload("session-1", "RF-123", "variant-1", 1);

    expect(payload).not.toHaveProperty("purchase_cost");
    expect(payload).not.toHaveProperty("selling_price");
    expect(payload).not.toHaveProperty("product_name");
    expect(payload).not.toHaveProperty("package_quantity");
  });

  it("allows multiple physical barcodes to point to one variant", () => {
    const first = existingVariantBarcodePayload("session-1", "0000456", "variant-1", 1);
    const second = existingVariantBarcodePayload("session-1", "0000457", "variant-1", 1);

    expect(first.product_variant_id).toBe(second.product_variant_id);
    expect(first.barcode).not.toBe(second.barcode);
  });
});

describe("newProductBarcodePayload", () => {
  it("normalizes blank optional UUID fields to null", () => {
    expect(newProductBarcodePayload("session-1", "8904481711450", form)).toMatchObject({
      action: "NEW_PRODUCT",
      category_id: "category-1",
      subcategory_id: null,
      brand_id: "brand-1",
    });
  });

  it("preserves the scanned barcode as a string with leading zeros", () => {
    expect(newProductBarcodePayload("session-1", "00008904481711450", form).barcode).toBe("00008904481711450");
  });

  it("refuses to send blank required UUID strings when validation is bypassed", () => {
    const invalidForm = {
      ...form,
      category_id: " ",
      subcategory_id: " ",
      brand_id: " ",
    };

    expect(() => newProductBarcodePayload("session-1", "8904481711450", invalidForm)).toThrow("Select a category");
  });
});

describe("newVariantBarcodePayload", () => {
  it("sends existing_product_id and variant data without product/category/brand fields", () => {
    const payload = newVariantBarcodePayload("session-1", "8904481711450", "product-1", form);

    expect(payload).toMatchObject({
      action: "NEW_VARIANT",
      existing_product_id: "product-1",
      size: "34/85 cm",
      selling_price: 395,
    });
    expect(payload).not.toHaveProperty("product_name");
    expect(payload).not.toHaveProperty("category_id");
    expect(payload).not.toHaveProperty("subcategory_id");
    expect(payload).not.toHaveProperty("brand_id");
  });
});

describe("validateBarcodeOnboarding", () => {
  it("requires a brand for a new product and identifies the field to focus", () => {
    expect(validateBarcodeOnboarding("NEW_PRODUCT", { ...form, brand_id: "" }, "", "")).toEqual({
      message: "Select a brand or choose Unbranded",
      field: "brand_id",
    });
  });

  it("allows same-price new variants when the identifying size is different", () => {
    const validation = validateBarcodeOnboarding("NEW_VARIANT", { ...form, size: "36/90 cm" }, "product-1", "");

    expect(validation).toBeNull();
  });

  it("rejects an invalid draft quantity instead of silently changing it", () => {
    expect(validateBarcodeOnboarding("NEW_VARIANT", { ...form, quantity: "0" }, "product-1", "")).toEqual({
      message: "Enter a quantity of at least 1",
      field: "quantity",
    });
  });

  it("validates quantity before assigning an existing variant", () => {
    expect(validateBarcodeOnboarding("EXISTING_VARIANT", { ...form, quantity: "0" }, "", "variant-1")).toEqual({
      message: "Enter a quantity of at least 1",
      field: "quantity",
    });
  });
});

describe("barcodeOnboardingErrorMessage", () => {
  it("hides raw UUID parsing errors behind field-specific guidance", () => {
    expect(barcodeOnboardingErrorMessage(new Error("brand_id: Input should be a valid UUID, invalid length: expected length 32"))).toBe("Select a brand or choose Unbranded");
  });

  it("maps duplicate variant responses to the assignment guidance", () => {
    expect(barcodeOnboardingErrorMessage({ code: "VARIANT_ALREADY_EXISTS" })).toBe("This variant already exists. Use Assign existing variant to add another barcode.");
  });
});

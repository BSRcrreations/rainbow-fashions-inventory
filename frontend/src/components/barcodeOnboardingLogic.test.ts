import { describe, expect, it } from "vitest";
import { existingVariantBarcodePayload } from "./barcodeOnboardingLogic";

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
});

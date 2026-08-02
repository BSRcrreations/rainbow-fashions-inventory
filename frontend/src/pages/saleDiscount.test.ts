import { describe, expect, it } from "vitest";

import { previewSaleDiscount, saleDiscountLabel } from "./saleDiscount";


describe("checkout sale discounts", () => {
  it("defaults naturally to a valid zero percentage discount", () => {
    expect(previewSaleDiscount(998, "PERCENTAGE", "0")).toMatchObject({ valid: true, discountAmount: 0, total: 998 });
  });

  it("calculates a 10% discount and grand total live", () => {
    expect(previewSaleDiscount(998, "PERCENTAGE", "10")).toMatchObject({ valid: true, discountAmount: 99.8, total: 898.2 });
    expect(saleDiscountLabel("PERCENTAGE", "10")).toBe("Discount (10%)");
  });

  it("supports decimal percentages and fixed amounts", () => {
    expect(previewSaleDiscount(998, "PERCENTAGE", "7.5")).toMatchObject({ valid: true, discountAmount: 74.85, total: 923.15 });
    expect(previewSaleDiscount(998, "FIXED_AMOUNT", "50")).toMatchObject({ valid: true, discountAmount: 50, total: 948 });
  });

  it("rejects invalid values without accepting scientific notation", () => {
    expect(previewSaleDiscount(998, "PERCENTAGE", "100.01")).toMatchObject({ valid: false, error: "Discount percentage must be between 0 and 100." });
    expect(previewSaleDiscount(998, "FIXED_AMOUNT", "998.01")).toMatchObject({ valid: false, error: "Discount amount cannot be greater than the subtotal." });
    expect(previewSaleDiscount(998, "PERCENTAGE", "1e1")).toMatchObject({ valid: false });
  });
});

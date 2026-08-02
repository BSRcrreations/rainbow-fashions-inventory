import { describe, expect, it } from "vitest";
import source from "./BatchBarcodeDialog.tsx?raw";


describe("manufacturer barcode batch scanning UI", () => {
  it("does not reject repeat scans as duplicate barcodes", () => {
    expect(source).not.toContain("This barcode was already scanned.");
    expect(source).not.toContain("Duplicate barcodes are not allowed in one batch");
  });

  it("shows staged-piece and distinct-variant totals with one review row per session item", () => {
    expect(source).toContain("Scanned pieces:");
    expect(source).toContain("Distinct variants:");
    expect(source).toContain("Conflicts:");
    expect(source).toContain("selectedItems.map");
    expect(source).toContain("item.scanned_quantity");
  });
});

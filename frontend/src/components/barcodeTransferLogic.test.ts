import { describe, expect, it } from "vitest";
import { barcodeTransferErrorMessage, canConfirmBarcodeTransfer, hasDuplicateBarcodes, parseTransferBarcodes, variantTransferLabel } from "./barcodeTransferLogic";

describe("barcode transfer helpers", () => {
  it("parses barcode values as strings and preserves leading zeroes", () => {
    expect(parseTransferBarcodes("08903289095861\n8903289095502")).toEqual(["08903289095861", "8903289095502"]);
  });

  it("detects duplicate barcode values", () => {
    expect(hasDuplicateBarcodes(["8903289095861", "8903289095861"])).toBe(true);
  });

  it("requires the exact MOVE TO S confirmation phrase", () => {
    expect(canConfirmBarcodeTransfer("MOVE TO S")).toBe(true);
    expect(canConfirmBarcodeTransfer("move to s")).toBe(false);
  });

  it("formats source and target variants for the preview", () => {
    expect(variantTransferLabel({ size: "M", color: "all", style_code: "Ankil" })).toBe("M / all / Ankil");
    expect(variantTransferLabel({ size: "S", color: "all", style_code: "Ankil" })).toBe("S / all / Ankil");
  });

  it("hides raw server codes behind clear messages", () => {
    expect(barcodeTransferErrorMessage({ code: "BARCODE_TARGET_PRODUCT_MISMATCH" })).toBe("Select the S variant from the same product.");
  });
});

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "src/pages/StockScanPage.tsx"), "utf8");

describe("confirmed Scan & Add Stock session", () => {
  it("defaults to product-first entry while retaining barcode-first entry", () => {
    expect(source).toContain('useState<"PRODUCT_FIRST" | "BARCODE_FIRST">("PRODUCT_FIRST")');
    expect(source).toContain("Select Product First");
    expect(source).toContain("Scan Barcode First");
    expect(source).toContain("ProductFirstStockEntry");
  });

  it("offers a shared-barcode exact-size choice instead of silently assigning stock", () => {
    expect(source).toContain("SHARED_BARCODE_SIZE_REQUIRED");
    expect(source).toContain("Choose the exact size before staging stock");
  });

  it("treats an unassigned barcode as available instead of a red error", () => {
    expect(source).toContain('title="Barcode available"');
    expect(source).toContain("is not currently assigned to any product.");
    expect(source).toContain(">Select Product</Button>");
    expect(source).toContain(">Create Product</Button>");
    expect(source).toContain('cause.code === "BARCODE_NOT_FOUND"');
  });
  it("shows a single read-only warning banner", () => {
    expect(source.match(/This stock session is confirmed and cannot be edited\./g)).toHaveLength(1);
  });

  it("replaces row editors with read-only scanned quantity and status", () => {
    expect(source).toContain('sessionLocked ? <span className="text-sm text-slate-600">Scanned quantity: {item.scanned_quantity}</span>');
    expect(source).toContain('sessionLocked ? <span className="text-sm font-medium text-slate-500">Confirmed</span>');
  });

  it("provides role-aware correction and navigation actions", () => {
    expect(source).toContain("Correct stock mistake");
    expect(source).toContain("View inventory history");
    expect(source).toContain("Manage product");
    expect(source).toContain("const canCorrect = canAssign");
  });

  it("starts a fresh session without changing the stored confirmed session", () => {
    expect(source).toContain("localStorage.removeItem(sessionKey(mode))");
    expect(source).toContain('setSessionId("")');
  });

  it("keeps one compact draft editor and a single remove action", () => {
    expect(source).toContain("DRAFT — NO INVENTORY MOVEMENT");
    expect(source).toContain('>Edit</Button>');
    expect(source).not.toContain("Change Product");
    expect(source).not.toContain("Change Variant");
    expect(source).not.toContain("Change Size");
    expect(source).not.toContain("Change Colour");
    expect(source).not.toContain("Change Barcode");
    expect(source).not.toContain("Change Quantity");
    expect(source).toContain("Remove staged item?");
    expect(source).toContain("sm:grid-cols-[minmax(0,1fr)_auto]");
    expect(source).toContain("Save Changes");
    expect(source).toContain("+ Add Variant");
  });

  it("sends draft version and handles shared and existing-variant corrections", () => {
    expect(source).toContain("expected_session_updated_at: session.updated_at");
    expect(source).toContain("SHARED_BARCODE_CONFIRMATION_REQUIRED");
    expect(source).toContain("DRAFT_VARIANT_ALREADY_EXISTS");
    expect(source).toContain("Use Existing");
  });
});

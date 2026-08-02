import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "src/pages/StockScanPage.tsx"), "utf8");

describe("confirmed Scan & Add Stock session", () => {
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
});

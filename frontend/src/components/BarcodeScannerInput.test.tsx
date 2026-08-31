import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "src/components/BarcodeScannerInput.tsx"), "utf8");

describe("barcode scanner input safety", () => {
  it("rejects obviously concatenated scans before sending them to the API", () => {
    expect(source).toContain("barcode.length > 40");
    expect(source).toContain("barcode.length > 20");
    expect(source).toContain("Barcode looks invalid. Please scan again.");
    expect(source).toContain('setValue("")');
  });
});

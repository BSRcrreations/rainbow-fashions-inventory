import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "src/components/BarcodeLookupDialog.tsx"), "utf8");

describe("barcode permanent-delete controls", () => {
  it("shows status, references, and an explicit irreversible confirmation", () => {
    expect(source).toContain("Active assignments:");
    expect(source).toContain("Historical references:");
    expect(source).toContain("Delete Barcode Permanently");
    expect(source).toContain("Permanently delete barcode");
    expect(source).toContain('confirmation: "DELETE BARCODE"');
  });
});

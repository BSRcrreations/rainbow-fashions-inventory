import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./AppLayout.tsx", import.meta.url), "utf8");

describe("global new sale shortcut", () => {
  it("is mounted once in the authenticated app layout and uses SPA navigation", () => {
    expect(source).toContain('location.pathname !== "/sales"');
    expect(source).toContain('aria-label="Start new sale"');
    expect(source).toContain('navigate("/sales")');
    expect(source).toContain('data-testid="new-sale-shortcut"');
  });
});

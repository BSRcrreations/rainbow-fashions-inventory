import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./App.tsx", import.meta.url), "utf8");

describe("application route compatibility", () => {
  it("uses the active dashboard and POS routes", () => {
    expect(source).toContain('<Route index element={<SalesDashboardPage />} />');
    expect(source).toContain('<Route path="/sales" element={<NewSalePage />} />');
    expect(source).toContain('<Route path="/sales/history" element={<SalesHistoryPage />} />');
  });

  it("retains supported redirects and unknown-path behavior", () => {
    expect(source).toContain('<Route path="/brands" element={<Navigate to="/categories" replace />} />');
    expect(source).toContain('<Route path="/stock-adjustment" element={<StockAdjustmentPage />} />');
    expect(source).toContain('<Route path="*" element={<Navigate to="/" replace />} />');
  });
});

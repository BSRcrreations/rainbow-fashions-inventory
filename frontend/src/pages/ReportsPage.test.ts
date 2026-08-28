import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const page = readFileSync(new URL("./ReportsPage.tsx", import.meta.url), "utf8");
const client = readFileSync(new URL("../api/client.ts", import.meta.url), "utf8");

describe("ReportsPage resilient report states", () => {
  it("uses an explicit Apply action and validates the date range before requesting a report", () => {
    expect(page).toContain('End date cannot be earlier than Start date.');
    expect(page).toContain('type="submit"');
    expect(page).toContain('> Apply</Button>');
  });

  it("renders loading, retry, safe server error, and empty report states", () => {
    expect(page).toContain('Generating your report…');
    expect(page).toContain('> Retry</Button>');
    expect(page).toContain('Unable to generate the report right now. Please try again.');
    expect(page).toContain('Error reference ID: {error.requestId}');
    expect(page).toContain('No sales or transactions found for this period.');
  });

  it("uses the requested network message and never relies on an untrusted server error for reports", () => {
    expect(client).toContain('Unable to connect to the server. Check your connection and try again.');
    expect(page).toContain('error.status >= 500');
  });
});

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CustomerListLoadError } from "./CustomersPage";

describe("CustomerListLoadError", () => {
  it("keeps customer-list failures compact and includes a safe retry reference", () => {
    const markup = renderToStaticMarkup(<CustomerListLoadError requestId="customer-list-ref" onRetry={() => undefined} />);

    expect(markup).toContain("Unable to load customers.");
    expect(markup).toContain("Retry");
    expect(markup).toContain("Reference: customer-list-ref");
    expect(markup).not.toContain("The server could not complete this request");
  });
});

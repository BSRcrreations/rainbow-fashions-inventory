// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import QuickEntryPage from "./QuickEntryPage";
import ThermalReceipt from "../components/ThermalReceipt";
import { draftKey, prepareSubmission, readDraft, writeDraft } from "../utils/draftStorage";
import { api } from "../api/client";
import type { Sale } from "../types";
const user = { id: "operator", store_id: "shop" };
vi.mock("../hooks/useAuth", () => ({ useAuth: () => ({ user: { id: "operator", store_id: "shop", role: "OWNER" } }) }));
vi.mock("../api/client", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
vi.mock("../hooks/useStoreSettings", () => ({ useStoreSettings: () => ({ data: { name: "Test Store", timezone: "Asia/Kolkata", receipt: { width_mm: 58, margin_mm: 2, copies: 2, show_gst: true, thank_you: "Visit again" } } }) }));
const key = draftKey(user, "quick-stock");
const draft = { sessionId: "session-1", documentId: "session-1", confirming: true, rows: [{ product: { name: "Cotton Leggings", product_id: "p1" }, variant: { variant_id: "large", size: "L", color: "Black" }, quantity: 3, cost: "10", price: "20" }], supplierId: "", supplierName: "", date: "2026-09-10", invoice: "", notes: "", payment: "CASH", paid: "0" };
beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); vi.mocked(api.get).mockResolvedValue([]); });
afterEach(cleanup);
function quick() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><QuickEntryPage /></MemoryRouter></QueryClientProvider>); }
it("recovers an uncertain stock confirmation after refresh, locks rows, and retries the original document", async () => {
  const actions = userEvent.setup(); writeDraft(key, draft); vi.mocked(api.post).mockRejectedValueOnce(new Error("Connection lost")).mockResolvedValueOnce({ status: "CONFIRMED" });
  let view = quick(); await actions.click(screen.getByRole("button", { name: "Continue" }));
  expect((screen.getByRole("button", { name: "Remove" }) as HTMLButtonElement).disabled).toBe(true);
  await actions.click(screen.getByRole("button", { name: "Save Stock" }));
  await actions.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save Stock" }));
  await screen.findByText("Connection lost"); view.unmount();
  view = quick(); await actions.click(screen.getByRole("button", { name: "Continue" }));
  await actions.click(screen.getByRole("button", { name: "Save Stock" }));
  await actions.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save Stock" }));
  await screen.findByText("Stock saved. Stock history is updated.");
  expect(vi.mocked(api.post).mock.calls.map((call) => call[0])).toEqual(["/stock-scan/sessions/session-1/confirm", "/stock-scan/sessions/session-1/confirm"]);
  await waitFor(() => expect(readDraft(key, draft).rows).toHaveLength(0)); view.unmount();
});
it("keeps the first submission key and payload across reload and changed input", () => {
  const first = prepareSubmission("bill", { quantity: 1 });
  const retry = prepareSubmission("bill", { quantity: 20 });
  expect(retry).toEqual(first); expect(retry.payload.quantity).toBe(1);
  expect(draftKey(user, "sale")).not.toBe(draftKey({ ...user, store_id: "other" }, "sale"));
});
it("prints a recorded bill with size, tax and configured width without submitting a transaction", async () => {
  const write = vi.fn(); const print = vi.fn(); const popup = { opener: {}, document: { write, close: vi.fn(), images: [] }, focus: vi.fn(), print };
  vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
  render(<ThermalReceipt sale={{ id: "sale", invoice_number: "RF-1", sale_date: "2026-09-10T04:00:00Z", payment_mode: "UPI", payment_reference: "ref-1", status: "COMPLETED", subtotal: "105", total_amount: "105", grand_total: "105", discount: "0", items: [{ id: "line", product_name: "Cotton Leggings", size_snapshot: "L", quantity: 1, unit_price: "105", line_total: "105", hsn_snapshot: "6115", gst_rate_snapshot: "5", taxable_value: "100", cgst_amount: "2.50", sgst_amount: "2.50" }] } as Sale} />);
  expect(screen.getByText("HSN 6115 · GST 5%")).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Print / Reprint Bill" }));
  expect(write.mock.calls[0][0]).toContain("size:58mm auto"); expect(write.mock.calls[0][0]).toContain("ref-1"); expect(print).toHaveBeenCalledTimes(1); expect(api.post).not.toHaveBeenCalled(); expect(popup.opener).toBe(null);
});

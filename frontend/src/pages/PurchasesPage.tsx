import { ChangeEvent, useEffect, useState } from "react";
import { Check, Upload } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import type { Purchase, PurchaseItem, PurchaseUploadResponse } from "../types";
import { money, shortDate } from "../utils/format";

export default function PurchasesPage() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [activePurchase, setActivePurchase] = useState<Purchase | null>(null);
  const [reviewItems, setReviewItems] = useState<PurchaseItem[]>([]);
  const [error, setError] = useState("");

  async function load() {
    setPurchases(await api.get<Purchase[]>("/purchases"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await api.post<PurchaseUploadResponse>("/purchases/upload", form);
      setActivePurchase(response.purchase);
      setReviewItems(response.review_items);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      event.target.value = "";
    }
  }

  function updateItem(index: number, key: keyof PurchaseItem, value: string) {
    setReviewItems((items) => items.map((item, i) => (i === index ? { ...item, [key]: key === "quantity" ? Number(value) : value } : item)));
  }

  async function confirm() {
    if (!activePurchase) return;
    const payload = {
      supplier_name: activePurchase.supplier_name,
      invoice_number: activePurchase.invoice_number,
      invoice_date: activePurchase.invoice_date,
      items: reviewItems
    };
    await api.put<Purchase>(`/purchases/${activePurchase.id}/review`, payload);
    const confirmed = await api.post<Purchase>(`/purchases/${activePurchase.id}/confirm`);
    setActivePurchase(confirmed);
    setReviewItems([]);
    await load();
  }

  return (
    <>
      <PageHeader
        title="Purchases"
        subtitle="Invoice intake and purchase history"
        actions={
          <label className="focus-ring inline-flex h-10 cursor-pointer items-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800">
            <Upload size={16} />
            Upload invoice
            <input className="hidden" type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(event) => void upload(event)} />
          </label>
        }
      />
      {error ? <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
      {activePurchase && reviewItems.length ? (
        <section className="mb-5 rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <div className="font-semibold text-slate-950">{activePurchase.supplier_name ?? "Supplier"}</div>
              <div className="text-sm text-slate-500">{activePurchase.invoice_number ?? "Invoice"}</div>
            </div>
            <button className="focus-ring inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white" onClick={() => void confirm()}>
              <Check size={16} /> Confirm
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Size</th>
                  <th className="px-3 py-2">Color</th>
                  <th className="px-3 py-2">Qty</th>
                  <th className="px-3 py-2">Purchase</th>
                  <th className="px-3 py-2">MRP</th>
                  <th className="px-3 py-2">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {reviewItems.map((item, index) => (
                  <tr key={`${item.product_name}-${index}`}>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-48 rounded-md border border-line px-2" value={item.product_name} onChange={(event) => updateItem(index, "product_name", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" value={item.size} onChange={(event) => updateItem(index, "size", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-28 rounded-md border border-line px-2" value={item.color} onChange={(event) => updateItem(index, "color", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-20 rounded-md border border-line px-2" type="number" min="1" value={item.quantity} onChange={(event) => updateItem(index, "quantity", event.target.value)} /></td>
                    <td className="px-3 py-2">{money(item.purchase_price)}</td>
                    <td className="px-3 py-2">{money(item.mrp)}</td>
                    <td className="px-3 py-2">{money(item.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      <div className="overflow-x-auto rounded-md border border-line bg-white">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Supplier</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {purchases.map((purchase) => (
              <tr key={purchase.id}>
                <td className="px-4 py-3">{purchase.invoice_number ?? "-"}</td>
                <td className="px-4 py-3">{purchase.supplier_name ?? "-"}</td>
                <td className="px-4 py-3">{shortDate(purchase.invoice_date)}</td>
                <td className="px-4 py-3">{money(purchase.total_amount)}</td>
                <td className="px-4 py-3"><StatusBadge value={purchase.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

import { ChangeEvent, useEffect, useState } from "react";
import { Check, ClipboardList, Upload } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Purchase, PurchaseItem, PurchaseUploadResponse } from "../types";
import { money, shortDate } from "../utils/format";

export default function PurchasesPage() {
  const toast = useToast();
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [activePurchase, setActivePurchase] = useState<Purchase | null>(null);
  const [reviewItems, setReviewItems] = useState<PurchaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setPurchases(await api.get<Purchase[]>("/purchases"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load purchases");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await api.post<PurchaseUploadResponse>("/purchases/upload", form);
      setActivePurchase(response.purchase);
      setReviewItems(response.review_items);
      toast.success("Invoice uploaded for review");
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setError(message);
      toast.error(message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  function updateItem(index: number, key: keyof PurchaseItem, value: string) {
    setReviewItems((items) =>
      items.map((item, i) => {
        if (i !== index) return item;
        const next = { ...item, [key]: key === "quantity" ? Number(value) : value };
        if (key === "quantity" || key === "purchase_price") {
          const qty = key === "quantity" ? Number(value) : Number(next.quantity);
          const price = key === "purchase_price" ? Number(value) : Number(next.purchase_price);
          next.line_total = String((Number.isFinite(qty) ? qty : 0) * (Number.isFinite(price) ? price : 0));
        }
        return next;
      })
    );
  }

  function validateReview() {
    if (!reviewItems.length) return "There are no review items to confirm";
    for (const [index, item] of reviewItems.entries()) {
      if (!item.product_name.trim()) return `Product name is required on line ${index + 1}`;
      if (!item.size.trim()) return `Size is required on line ${index + 1}`;
      if (!item.color.trim()) return `Color is required on line ${index + 1}`;
      if (!Number.isInteger(Number(item.quantity)) || Number(item.quantity) <= 0) return `Quantity must be positive on line ${index + 1}`;
      if (!Number.isFinite(Number(item.purchase_price)) || Number(item.purchase_price) < 0) return `Purchase price is invalid on line ${index + 1}`;
    }
    return "";
  }

  async function confirm() {
    if (!activePurchase) return;
    const validationError = validateReview();
    if (validationError) {
      setError(validationError);
      return;
    }
    setConfirming(true);
    setError("");
    try {
      const payload = {
        supplier_name: activePurchase.supplier_name,
        invoice_number: activePurchase.invoice_number,
        invoice_date: activePurchase.invoice_date,
        items: reviewItems,
      };
      await api.put<Purchase>(`/purchases/${activePurchase.id}/review`, payload);
      const confirmed = await api.post<Purchase>(`/purchases/${activePurchase.id}/confirm`);
      setActivePurchase(confirmed);
      setReviewItems([]);
      toast.success("Purchase confirmed and stock updated");
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Purchase confirmation failed";
      setError(message);
      toast.error(message);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Purchases"
        subtitle="Invoice intake and purchase history"
        actions={
          <label className={`focus-ring inline-flex h-10 cursor-pointer items-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 ${uploading ? "pointer-events-none opacity-60" : ""}`}>
            <Upload size={16} />
            {uploading ? "Uploading" : "Upload invoice"}
            <input className="hidden" type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(event) => void upload(event)} disabled={uploading} />
          </label>
        }
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {activePurchase && reviewItems.length ? (
        <section className="mb-5 rounded-md border border-line bg-white">
          <div className="grid gap-3 border-b border-line px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div className="min-w-0">
              <div className="truncate font-semibold text-slate-950">{activePurchase.supplier_name ?? "Supplier"}</div>
              <div className="truncate text-sm text-slate-500">{activePurchase.invoice_number ?? "Invoice"}</div>
            </div>
            <Button type="button" variant="secondary" onClick={() => void confirm()} disabled={confirming}>
              <Check size={16} /> {confirming ? "Confirming" : "Confirm"}
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[860px] divide-y divide-line text-sm">
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
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" type="number" min="0" step="0.01" value={item.purchase_price} onChange={(event) => updateItem(index, "purchase_price", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" type="number" min="0" step="0.01" value={item.mrp ?? ""} onChange={(event) => updateItem(index, "mrp", event.target.value)} /></td>
                    <td className="px-3 py-2">{money(item.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {loading ? (
        <SkeletonRows rows={6} />
      ) : purchases.length ? (
        <div className="overflow-x-auto rounded-md border border-line bg-white">
          <table className="min-w-[720px] divide-y divide-line text-sm">
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
      ) : (
        <div className="rounded-md border border-line bg-white">
          <EmptyState icon={ClipboardList} title="No purchases yet" description="Upload an invoice, review OCR results, edit lines if needed, then confirm to update stock." />
        </div>
      )}
    </>
  );
}

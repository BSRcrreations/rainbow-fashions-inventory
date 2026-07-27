import { ChangeEvent, useEffect, useRef, useState } from "react";
import { Check, ClipboardList, RefreshCw, ScanLine } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Purchase, PurchaseDocumentAccepted, PurchaseDocumentJob, PurchaseItem, PurchaseUploadResponse } from "../types";
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
  const [processing, setProcessing] = useState<PurchaseDocumentJob | null>(null);
  const pollTimer = useRef<number | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [invoiceDate, setInvoiceDate] = useState("");
  const [receivedDate, setReceivedDate] = useState("");

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
    return () => { if (pollTimer.current !== null) window.clearTimeout(pollTimer.current); };
  }, []);

  async function pollJob(jobId: string) {
    try {
      const job = await api.get<PurchaseDocumentJob>(`/purchase-documents/jobs/${jobId}`);
      setProcessing(job);
      if (job.status === "FAILED") {
        setError(`${job.error_message ?? "Invoice recognition failed"}${job.request_id ? ` Reference: ${job.request_id}` : ""}`);
        return;
      }
      if (job.status === "REVIEW_REQUIRED" || job.status === "COMPLETED") {
        const response = await api.post<PurchaseUploadResponse>("/purchases/from-document", { job_id: job.id });
        setActivePurchase(response.purchase);
        setReviewItems(response.review_items);
        setPurchaseDate(response.purchase.purchase_date);
        setInvoiceDate(response.purchase.invoice_date ?? "");
        setReceivedDate(response.purchase.received_date ?? "");
        setDuplicateWarning(response.duplicate_warning ?? "");
        setProcessing(null);
        toast.success("Invoice draft is ready for review");
        await load();
        return;
      }
      pollTimer.current = window.setTimeout(() => { void pollJob(jobId); }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Invoice processing failed";
      setError(message);
      toast.error(message);
    }
  }

  async function retryProcessing() {
    if (!processing || processing.status !== "FAILED") return;
    try {
      const job = await api.post<PurchaseDocumentJob>(`/purchase-documents/${processing.document_id}/retry`);
      setError("");
      setProcessing(job);
      toast.success("Invoice recognition retry started");
      await pollJob(job.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not retry invoice recognition";
      setError(message);
      toast.error(message);
    }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await api.post<PurchaseDocumentAccepted>("/purchase-documents/upload", form);
      toast.success("Invoice uploaded. Recognition has started.");
      await pollJob(response.job_id);
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
        purchase_date: purchaseDate,
        invoice_date: invoiceDate || null,
        received_date: receivedDate || null,
        duplicate_acknowledged: Boolean(duplicateWarning),
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
            <ScanLine size={16} />
            {uploading ? "Scanning" : "Scan invoice / add picture"}
            <input className="hidden" type="file" accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.pdf,image/heic,image/heif,image/webp,application/pdf" capture="environment" onChange={(event) => void upload(event)} disabled={uploading} />
          </label>
        }
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {processing ? <section className="mb-5 rounded-lg border border-line bg-white p-4"><div className="flex items-center justify-between gap-4"><div><div className="font-semibold">{processing.status === "FAILED" ? "Invoice recognition needs attention" : "Processing invoice"}</div><div className="mt-1 text-sm text-muted">{processing.message}</div></div><strong>{processing.progress}%</strong></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full transition-all ${processing.status === "FAILED" ? "bg-red-500" : "bg-primary"}`} style={{ width: `${processing.progress}%` }} /></div>{processing.status === "FAILED" ? <div className="mt-3"><Button type="button" variant="secondary" onClick={() => void retryProcessing()}><RefreshCw size={16} /> Retry recognition</Button></div> : null}</section> : null}
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
          {duplicateWarning ? <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{duplicateWarning}</div> : null}
          <div className="grid gap-3 border-b border-line px-4 py-3 sm:grid-cols-3"><label className="field-label">Purchase date<input required type="date" className="field-input" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} /></label><label className="field-label">Invoice date<input type="date" className="field-input" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} /></label><label className="field-label">Received date<input type="date" className="field-input" value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} /></label></div>
          <div className="overflow-x-auto">
            <table className="min-w-[860px] divide-y divide-line text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Match</th>
                  <th className="px-3 py-2">Barcode / SKU</th>
                  <th className="px-3 py-2">Size</th>
                  <th className="px-3 py-2">Color</th>
                  <th className="px-3 py-2">Qty</th>
                  <th className="px-3 py-2">Unit</th>
                  <th className="px-3 py-2">Purchase</th>
                  <th className="px-3 py-2">MRP</th>
                  <th className="px-3 py-2">Total</th>
                  <th className="px-3 py-2">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {reviewItems.map((item, index) => (
                  <tr key={`${item.product_name}-${index}`}>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-48 rounded-md border border-line px-2" value={item.product_name} onChange={(event) => updateItem(index, "product_name", event.target.value)} /></td>
                    <td className="px-3 py-2 text-xs font-semibold">{item.match_status.replace(/_/g, " ")}</td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-28 rounded-md border border-line px-2" value={item.barcode ?? item.supplier_product_code ?? ""} onChange={(event) => updateItem(index, "barcode", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" value={item.size} onChange={(event) => updateItem(index, "size", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-28 rounded-md border border-line px-2" value={item.color} onChange={(event) => updateItem(index, "color", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-20 rounded-md border border-line px-2" type="number" min="1" value={item.quantity} onChange={(event) => updateItem(index, "quantity", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-20 rounded-md border border-line px-2" value={item.unit} onChange={(event) => updateItem(index, "unit", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" type="number" min="0" step="0.01" value={item.purchase_price} onChange={(event) => updateItem(index, "purchase_price", event.target.value)} /></td>
                    <td className="px-3 py-2"><input className="focus-ring h-9 w-24 rounded-md border border-line px-2" type="number" min="0" step="0.01" value={item.mrp ?? ""} onChange={(event) => updateItem(index, "mrp", event.target.value)} /></td>
                    <td className="px-3 py-2">{money(item.line_total)}</td>
                    <td className="px-3 py-2 text-xs">{item.confidence ? `${Math.round(Number(item.confidence) * 100)}%` : "Manual"}</td>
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
                <th className="px-4 py-3">Purchase date</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {purchases.map((purchase) => (
                <tr key={purchase.id}>
                  <td className="px-4 py-3">{purchase.invoice_number ?? "-"}</td>
                  <td className="px-4 py-3">{purchase.supplier_name ?? "-"}</td>
                  <td className="px-4 py-3">{shortDate(purchase.purchase_date)}</td>
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

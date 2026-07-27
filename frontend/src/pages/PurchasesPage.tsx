import { ChangeEvent, useEffect, useRef, useState } from "react";
import { Ban, CheckCircle2, ExternalLink, Eye, FileSearch, Pencil, RefreshCw, ScanLine } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Purchase, PurchaseDocumentAccepted, PurchaseDocumentJob, PurchaseUploadResponse } from "../types";
import { money, shortDate } from "../utils/format";

export default function PurchasesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState<PurchaseDocumentJob | null>(null);
  const [error, setError] = useState("");
  const pollTimer = useRef<number | null>(null);

  async function load() {
    try {
      setError("");
      setPurchases((await api.get<Purchase[]>("/purchases")) ?? []);
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
        toast.success("Purchase draft is ready for review");
        navigate(`/purchases/${response.purchase.id}`);
        return;
      }
      pollTimer.current = window.setTimeout(() => { void pollJob(jobId); }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Invoice processing failed";
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

  async function retry(purchase: Purchase) {
    if (!purchase.purchase_document_id) {
      navigate(`/purchases/${purchase.id}`);
      return;
    }
    try {
      const job = await api.post<PurchaseDocumentJob>(`/purchase-documents/${purchase.purchase_document_id}/retry`);
      setProcessing(job);
      toast.success("Recognition retry started");
      await pollJob(job.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not retry recognition");
    }
  }

  return (
    <>
      <PageHeader
        title="Purchases"
        subtitle="Invoice intake, review, and stock confirmation"
        actions={<label className={`focus-ring inline-flex h-control cursor-pointer items-center gap-2 rounded-lg bg-primary-700 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-800 ${uploading ? "pointer-events-none opacity-60" : ""}`}><ScanLine size={18} />{uploading ? "Uploading" : "Upload invoice"}<input className="hidden" type="file" accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.pdf,image/heic,image/heif,image/webp,application/pdf" capture="environment" onChange={(event) => void upload(event)} disabled={uploading} /></label>}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {processing ? <section className="ds-surface mb-5 p-4"><div className="flex items-center justify-between gap-4"><div><div className="font-semibold">{processing.status === "FAILED" ? "Recognition needs attention" : "Processing invoice"}</div><div className="mt-1 text-sm text-muted">{processing.message}</div></div><strong>{processing.progress}%</strong></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full transition-all ${processing.status === "FAILED" ? "bg-error" : "bg-primary-600"}`} style={{ width: `${processing.progress}%` }} /></div></section> : null}
      {loading ? <SkeletonRows rows={6} /> : purchases.length ? (
        <div className="ds-table-wrap overflow-x-auto">
          <table className="ds-table min-w-[1180px]">
            <thead><tr><th>Invoice</th><th>Supplier</th><th>Invoice date</th><th>Purchase date</th><th className="text-right">Qty</th><th className="text-right">Invoice total</th><th className="text-right">Paid</th><th className="text-right">Balance</th><th>Processing</th><th>Purchase</th><th>Created</th><th>Updated</th><th className="sticky right-0 bg-surface-subtle">Actions</th></tr></thead>
            <tbody>{purchases.map((purchase) => (
              <tr key={purchase.id} className="cursor-pointer" onClick={() => navigate(`/purchases/${purchase.id}`)}>
                <td className="font-semibold text-foreground">{purchase.invoice_number || "Invoice pending"}</td><td>{purchase.supplier_name || "Supplier pending"}</td><td>{shortDate(purchase.invoice_date)}</td><td>{shortDate(purchase.purchase_date)}</td><td className="text-right">{purchase.total_quantity}</td><td className="text-right">{money(purchase.total_amount)}</td><td className="text-right">{money(purchase.amount_paid)}</td><td className="text-right">{money(purchase.balance_due)}</td><td><StatusBadge value={purchase.workflow_status} /></td><td><StatusBadge value={purchase.status} /></td><td>{shortDate(purchase.created_at)}</td><td>{shortDate(purchase.updated_at)}</td>
                <td className="sticky right-0 bg-inherit" onClick={(event) => event.stopPropagation()}><div className="flex gap-1"><Button aria-label="View purchase" title="View purchase" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}`)}><Eye size={17} /></Button><Button aria-label="Edit purchase" title="Edit purchase" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}?edit=1`)}><Pencil size={17} /></Button><Button aria-label="Open invoice" title="Open invoice" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}#invoice-preview`)}><ExternalLink size={17} /></Button><Button aria-label="Retry recognition" title="Retry recognition" size="icon" variant="ghost" disabled={purchase.status === "CONFIRMED"} onClick={() => void retry(purchase)}><RefreshCw size={17} /></Button><Button aria-label="Confirm purchase" title="Confirm purchase" size="icon" variant="ghost" disabled={purchase.status !== "DRAFT" && purchase.status !== "REVIEWED"} onClick={() => navigate(`/purchases/${purchase.id}#confirm-purchase`)}><CheckCircle2 size={17} /></Button><Button aria-label="Cancel purchase" title="Cancel purchase" size="icon" variant="ghost" disabled={purchase.status === "CONFIRMED" || purchase.status === "CANCELLED"} onClick={() => navigate(`/purchases/${purchase.id}#cancel-purchase`)}><Ban size={17} /></Button></div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : <div className="ds-surface"><EmptyState icon={FileSearch} title="No purchases have been added yet." description="Upload an invoice to create a reviewable purchase draft." /></div>}
    </>
  );
}

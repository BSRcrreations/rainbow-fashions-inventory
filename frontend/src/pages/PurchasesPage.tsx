import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";
import { Ban, CheckCircle2, ExternalLink, Eye, FileSearch, Pencil, RefreshCw, ScanLine, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ApiError } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import DeletePasswordDialog from "../components/DeletePasswordDialog";
import { useAuth } from "../hooks/useAuth";
import type { Purchase, PurchaseDocumentAccepted, PurchaseDocumentJob, PurchaseUploadResponse } from "../types";
import { money, shortDate } from "../utils/format";

export default function PurchasesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState<PurchaseDocumentJob | null>(null);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleteIds, setDeleteIds] = useState<string[]>([]);
  const [deleteSummary, setDeleteSummary] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleteRequestId, setDeleteRequestId] = useState<string | undefined>();
  const pollTimer = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      setError("");
      const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
      setPurchases((await api.get<Purchase[]>(`/purchases${query}`)) ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load purchases");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
    return () => { if (pollTimer.current !== null) window.clearTimeout(pollTimer.current); };
  }, [load]);

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

  async function beginDelete(ids: string[]) {
    try {
      setDeleteError(""); setDeleteRequestId(undefined);
      const check = await api.post<{ deletable: Array<{ reference: string }>; requires_void: Array<{ reference: string }>; blocked: Array<{ reason: string }> }>("/purchases/delete-check", { purchase_ids: ids });
      if (check.blocked.length) { toast.error(check.blocked[0].reason); return; }
      setDeleteIds(ids);
      setDeleteSummary(`${check.deletable.length} will be permanently deleted and ${check.requires_void.length} will be voided with inventory reversal.`);
    } catch (err) { toast.error(err instanceof Error ? err.message : "Unable to check purchases"); }
  }

  async function confirmDelete(password: string) {
    setDeleting(true);
    try {
      const result = await api.post<{ deleted: unknown[]; voided: unknown[] }>("/purchases/delete", { purchase_ids: deleteIds, delete_password: password }, { "Idempotency-Key": crypto.randomUUID() });
      toast.success(`${result.deleted.length} purchases deleted, ${result.voided.length} voided`);
      setDeleteIds([]); setSelectedIds(new Set()); await load();
    } catch (err) { const message = err instanceof Error ? err.message : "Unable to delete purchases"; setDeleteError(message); setDeleteRequestId(err instanceof ApiError ? err.requestId : undefined); toast.error(message); } finally { setDeleting(false); }
  }

  return (
    <>
      <PageHeader
        title="Purchases"
        subtitle="Invoice intake, review, and stock confirmation"
        actions={<label className={`focus-ring inline-flex h-control cursor-pointer items-center gap-2 rounded-lg bg-primary-700 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-800 ${uploading ? "pointer-events-none opacity-60" : ""}`}><ScanLine size={18} />{uploading ? "Uploading" : "Upload invoice"}<input className="hidden" type="file" accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.pdf,image/heic,image/heif,image/webp,application/pdf" capture="environment" onChange={(event) => void upload(event)} disabled={uploading} /></label>}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><label className="flex items-center gap-2 text-sm font-medium text-muted">Status<select aria-label="Purchase status" className="field-input h-10 w-auto" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setSelectedIds(new Set()); setLoading(true); }}><option value="">All</option><option value="DRAFT">Draft</option><option value="REVIEW_REQUIRED">Review required</option><option value="CONFIRMED">Confirmed</option><option value="CANCELLED">Cancelled</option><option value="VOIDED">Voided</option><option value="FAILED">Failed</option></select></label></div>
      {user?.role === "OWNER" && selectedIds.size ? <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 p-3 text-sm font-semibold text-primary-900"><span>{selectedIds.size} purchases selected</span><Button size="sm" variant="secondary" onClick={() => setSelectedIds(new Set())}>Clear selection</Button><Button size="sm" variant="destructive" onClick={() => void beginDelete(Array.from(selectedIds))}><Trash2 size={16} /> Delete selected</Button></div> : null}
      {processing ? <section className="ds-surface mb-5 p-4"><div className="flex items-center justify-between gap-4"><div><div className="font-semibold">{processing.status === "FAILED" ? "Recognition needs attention" : "Processing invoice"}</div><div className="mt-1 text-sm text-muted">{processing.message}</div></div><strong>{processing.progress}%</strong></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full transition-all ${processing.status === "FAILED" ? "bg-error" : "bg-primary-600"}`} style={{ width: `${processing.progress}%` }} /></div></section> : null}
      {loading ? <SkeletonRows rows={6} /> : purchases.length ? (
        <div className="ds-table-wrap overflow-x-auto">
          <table className="ds-table min-w-[1180px]">
            <thead><tr>{user?.role === "OWNER" ? <th><input aria-label="Select all purchases on page" type="checkbox" checked={purchases.length > 0 && selectedIds.size === purchases.length} onChange={(event) => setSelectedIds(event.target.checked ? new Set(purchases.map((purchase) => purchase.id)) : new Set())} /></th> : null}<th>Invoice</th><th>Supplier</th><th>Invoice date</th><th>Purchase date</th><th className="text-right">Qty</th><th className="text-right">Invoice total</th><th className="text-right">Paid</th><th className="text-right">Balance</th><th>Processing</th><th>Purchase</th><th>Created</th><th>Updated</th><th className="">Actions</th></tr></thead>
            <tbody>{purchases.map((purchase) => (
              <tr key={purchase.id} className="cursor-pointer" onClick={() => navigate(`/purchases/${purchase.id}`)}>
                {user?.role === "OWNER" ? <td onClick={(event) => event.stopPropagation()}><input aria-label={`Select ${purchase.invoice_number || "purchase"}`} type="checkbox" checked={selectedIds.has(purchase.id)} onChange={(event) => setSelectedIds((current) => { const next = new Set(current); if (event.target.checked) next.add(purchase.id); else next.delete(purchase.id); return next; })} /></td> : null}<td className="font-semibold text-foreground">{purchase.invoice_number || "Invoice pending"}</td><td>{purchase.supplier_name || "Supplier pending"}</td><td>{shortDate(purchase.invoice_date)}</td><td>{shortDate(purchase.purchase_date)}</td><td className="text-right">{purchase.total_quantity}</td><td className="text-right">{money(purchase.total_amount)}</td><td className="text-right">{money(purchase.amount_paid)}</td><td className="text-right">{money(purchase.balance_due)}</td><td><StatusBadge value={purchase.workflow_status} /></td><td><StatusBadge value={purchase.status} /></td><td>{shortDate(purchase.created_at)}</td><td>{shortDate(purchase.updated_at)}</td>
                <td onClick={(event) => event.stopPropagation()}><div className="flex min-w-max gap-1"><Button aria-label="View purchase" title="View purchase" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}`)}><Eye size={17} /></Button><Button aria-label="Edit purchase" title="Edit purchase" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}?edit=1`)}><Pencil size={17} /></Button><Button aria-label="Open invoice" title="Open invoice" size="icon" variant="ghost" onClick={() => navigate(`/purchases/${purchase.id}#invoice-preview`)}><ExternalLink size={17} /></Button><Button aria-label="Retry recognition" title="Retry recognition" size="icon" variant="ghost" disabled={purchase.status === "CONFIRMED"} onClick={() => void retry(purchase)}><RefreshCw size={17} /></Button><Button aria-label="Confirm purchase" title="Confirm purchase" size="icon" variant="ghost" disabled={purchase.status !== "DRAFT" && purchase.status !== "REVIEWED"} onClick={() => navigate(`/purchases/${purchase.id}#confirm-purchase`)}><CheckCircle2 size={17} /></Button><Button aria-label="Cancel purchase" title="Cancel purchase" size="icon" variant="ghost" disabled={purchase.status === "CONFIRMED" || purchase.status === "CANCELLED"} onClick={() => navigate(`/purchases/${purchase.id}#cancel-purchase`)}><Ban size={17} /></Button>{user?.role === "OWNER" ? <Button aria-label="Delete purchase" title="Delete purchase" size="icon" variant="ghost" onClick={() => void beginDelete([purchase.id])}><Trash2 size={17} /></Button> : null}</div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : <div className="ds-surface"><EmptyState icon={FileSearch} title="No purchases have been added yet." description="Upload an invoice to create a reviewable purchase draft." /></div>}
      <DeletePasswordDialog open={deleteIds.length > 0} title={`Delete ${deleteIds.length} purchase${deleteIds.length === 1 ? "" : "s"}?`} summary={deleteSummary} submitLabel="Delete purchase" loading={deleting} error={deleteError} requestId={deleteRequestId} onClose={() => { setDeleteIds([]); setDeleteError(""); setDeleteRequestId(undefined); }} onSubmit={(password) => void confirmDelete(password)} />
    </>
  );
}

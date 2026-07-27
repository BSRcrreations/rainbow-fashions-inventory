import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, ClipboardCheck, Download, FileText, Pencil, Plus, RotateCcw, Save, Trash2, X } from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Purchase, PurchaseDetail, PurchaseItem } from "../types";
import { money, shortDate } from "../utils/format";

type HeaderField = "supplier_name" | "invoice_number" | "purchase_date" | "invoice_date" | "received_date" | "due_date" | "payment_mode" | "amount_paid" | "place_of_supply" | "purchase_reference" | "notes" | "warehouse" | "currency" | "packaging_amount" | "freight_amount" | "round_off";
type ItemField = "product_name" | "barcode" | "supplier_product_code" | "hsn_sac" | "size" | "color" | "quantity" | "unit" | "purchase_price" | "discount" | "tax_rate" | "tax_amount" | "mrp";

function blankItem(): PurchaseItem {
  return { product_name: "", unit: "Each", size: "", color: "", quantity: 1, purchase_price: "0", discount: "0", tax_amount: "0", tax_rate: "0", line_total: "0", match_status: "MANUAL", user_verified: true };
}

function itemTotal(item: PurchaseItem): string {
  const quantity = Number(item.quantity) || 0;
  const price = Number(item.purchase_price) || 0;
  const discount = Number(item.discount) || 0;
  const tax = Number(item.tax_amount) || 0;
  return (quantity * price - discount + tax).toFixed(2);
}

function draftFrom(purchase: PurchaseDetail): PurchaseDetail {
  return { ...purchase, items: purchase.items.map((item) => ({ ...item })) };
}

function itemChanged(original: PurchaseItem, next: PurchaseItem): boolean {
  const fields: Array<keyof PurchaseItem> = ["product_name", "barcode", "supplier_product_code", "hsn_sac", "unit", "size", "color", "quantity", "purchase_price", "discount", "tax_rate", "tax_amount", "mrp"];
  return fields.some((field) => String(original[field] ?? "") !== String(next[field] ?? ""));
}

export default function PurchaseDetailPage() {
  const { purchaseId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [purchase, setPurchase] = useState<PurchaseDetail | null>(null);
  const [draft, setDraft] = useState<PurchaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(searchParams.get("edit") === "1");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<string[]>([]);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [documentUrl, setDocumentUrl] = useState("");

  const editable = Boolean(purchase && purchase.status !== "CONFIRMED" && purchase.status !== "CANCELLED");

  const load = useCallback(async () => {
    if (!purchaseId) return;
    try {
      setError("");
      const response = await api.get<PurchaseDetail>(`/purchases/${purchaseId}`);
      setPurchase(response);
      setDraft(draftFrom(response));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load purchase details");
    } finally {
      setLoading(false);
    }
  }, [purchaseId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!purchaseId || !purchase?.document) return;
    let currentUrl = "";
    void api.getBlob(`/purchases/${purchaseId}/document`).then((blob) => { currentUrl = URL.createObjectURL(blob); setDocumentUrl(currentUrl); }).catch(() => setDocumentUrl(""));
    return () => { if (currentUrl) URL.revokeObjectURL(currentUrl); };
  }, [purchaseId, purchase?.document]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const totals = useMemo(() => {
    if (!draft) return { quantity: 0, subtotal: 0, discount: 0, tax: 0, total: 0 };
    const quantity = draft.items.reduce((total, item) => total + (Number(item.quantity) || 0), 0);
    const subtotal = draft.items.reduce((total, item) => total + (Number(item.quantity) || 0) * (Number(item.purchase_price) || 0), 0);
    const discount = draft.items.reduce((total, item) => total + (Number(item.discount) || 0), 0);
    const tax = draft.items.reduce((total, item) => total + (Number(item.tax_amount) || 0), 0);
    const total = subtotal - discount + tax + (Number(draft.packaging_amount) || 0) + (Number(draft.freight_amount) || 0) + (Number(draft.round_off) || 0);
    return { quantity, subtotal, discount, tax, total };
  }, [draft]);

  function updateHeader(field: HeaderField, value: string) {
    setDraft((current) => current ? { ...current, [field]: value } : current);
    setDirty(true);
  }

  function updateItem(index: number, field: ItemField, value: string) {
    setDraft((current) => {
      if (!current) return current;
      const items = current.items.map((item, itemIndex) => {
        if (itemIndex !== index) return item;
        const next: PurchaseItem = { ...item, [field]: field === "quantity" ? Number(value) : value };
        if (field === "tax_rate") next.tax_amount = (((Number(next.quantity) || 0) * (Number(next.purchase_price) || 0) - (Number(next.discount) || 0)) * (Number(value) || 0) / 100).toFixed(2);
        next.line_total = itemTotal(next);
        return next;
      });
      return { ...current, items };
    });
    setDirty(true);
  }

  function removeItem(index: number) {
    setDraft((current) => current ? { ...current, items: current.items.filter((_, itemIndex) => itemIndex !== index) } : current);
    setDirty(true);
  }

  function startEditing() {
    if (!editable) return;
    setDraft(purchase ? draftFrom(purchase) : null);
    setEditing(true);
    setDirty(false);
    setValidation([]);
  }

  function discardEdits() {
    if (dirty && !window.confirm("Discard unsaved purchase changes?")) return;
    setDraft(purchase ? draftFrom(purchase) : null);
    setEditing(false);
    setDirty(false);
    setValidation([]);
  }

  async function validatePurchase() {
    if (!purchase) return false;
    try {
      const response = await api.post<{ valid: boolean; messages: string[] }>(`/purchases/${purchase.id}/validate`);
      setValidation(response.messages);
      if (response.valid) toast.success("Purchase is ready to confirm");
      return response.valid;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not validate purchase");
      return false;
    }
  }

  async function save() {
    if (!purchase || !draft) return;
    if (!draft.invoice_number?.trim()) { setValidation(["Enter the supplier invoice number."]); return; }
    if (!draft.items.length) { setValidation(["Add at least one purchase item."]); return; }
    setSaving(true);
    setError("");
    try {
      const headerChanged = (["supplier_name", "invoice_number", "purchase_date", "invoice_date", "received_date", "due_date", "payment_mode", "amount_paid", "place_of_supply", "purchase_reference", "notes", "warehouse", "currency", "packaging_amount", "freight_amount", "round_off"] as HeaderField[]).some((field) => String(purchase[field] ?? "") !== String(draft[field] ?? ""));
      let current: Purchase = purchase;
      if (headerChanged) current = await api.patch(`/purchases/${purchase.id}`, {
        supplier_name: draft.supplier_name || null, invoice_number: draft.invoice_number.trim(), purchase_date: draft.purchase_date, invoice_date: draft.invoice_date || null, received_date: draft.received_date || null, due_date: draft.due_date || null, payment_mode: draft.payment_mode, amount_paid: draft.amount_paid, place_of_supply: draft.place_of_supply || null, purchase_reference: draft.purchase_reference || null, notes: draft.notes || null, warehouse: draft.warehouse || null, currency: draft.currency, packaging_amount: draft.packaging_amount, freight_amount: draft.freight_amount, round_off: draft.round_off, version: purchase.version, reason: "Purchase details updated",
      });
      const originalIds = new Set(purchase.items.flatMap((item) => item.id ? [item.id] : []));
      const draftIds = new Set(draft.items.flatMap((item) => item.id ? [item.id] : []));
      for (const id of originalIds) if (!draftIds.has(id)) current = await api.delete<Purchase>(`/purchases/${purchase.id}/items/${id}?version=${current.version}`);
      for (const item of draft.items) {
        const original = item.id ? purchase.items.find((candidate) => candidate.id === item.id) : undefined;
        if (item.id && original && !itemChanged(original, item)) continue;
        const payload = { ...item, version: current.version, reason: "Purchase item updated" };
        current = item.id ? await api.patch<Purchase>(`/purchases/${purchase.id}/items/${item.id}`, payload) : await api.post<Purchase>(`/purchases/${purchase.id}/items`, payload);
      }
      toast.success("Purchase draft saved");
      setEditing(false);
      setDirty(false);
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save purchase changes";
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  async function confirmPurchase() {
    if (!purchase) return;
    const isValid = await validatePurchase();
    if (!isValid) { setConfirmOpen(false); return; }
    setSaving(true);
    try {
      await api.post<Purchase>(`/purchases/${purchase.id}/confirm`);
      toast.success("Purchase confirmed and stock updated once");
      setConfirmOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm purchase");
    } finally { setSaving(false); }
  }

  async function cancelPurchase() {
    if (!purchase || cancelReason.trim().length < 3) { setError("Enter a cancellation reason."); return; }
    setSaving(true);
    try {
      await api.post<Purchase>(`/purchases/${purchase.id}/cancel`, { reason: cancelReason.trim(), version: purchase.version });
      toast.success("Purchase cancelled");
      setCancelOpen(false);
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not cancel purchase"); } finally { setSaving(false); }
  }

  async function downloadInvoice() {
    if (!purchase) return;
    try {
      const blob = await api.getBlob(`/purchases/${purchase.id}/document?download=true`);
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = purchase.document?.original_filename ?? "invoice"; anchor.click(); URL.revokeObjectURL(url);
    } catch (err) { setError(err instanceof Error ? err.message : "Invoice document is unavailable"); }
  }

  if (loading) return <SkeletonRows rows={8} />;
  if (!purchase || !draft) return <ErrorState message={error || "Purchase not found"} />;

  return <>
    <PageHeader title="Purchase Details" subtitle={purchase.invoice_number || "Invoice number pending"} actions={<div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={() => { if (!dirty || window.confirm("Discard unsaved purchase changes?")) navigate("/purchases"); }}><ArrowLeft size={16} /> Back</Button>{editable && !editing ? <Button onClick={startEditing}><Pencil size={16} /> Edit</Button> : null}</div>} />
    {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
    {validation.length ? <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>Review required</strong><ul className="mt-1 list-disc pl-5">{validation.map((message) => <li key={message}>{message}</li>)}</ul></div> : null}
    <section className="ds-surface mb-5 flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><StatusBadge value={purchase.workflow_status} /><StatusBadge value={purchase.status} /></div><p className="mt-2 text-sm text-muted">Created {shortDate(purchase.created_at)} · Updated {shortDate(purchase.updated_at)}{purchase.confirmed_at ? ` · Confirmed ${shortDate(purchase.confirmed_at)}` : ""}</p></div><div className="text-sm text-muted">Version {purchase.version}</div></section>
    <div className="grid gap-5 xl:grid-cols-[minmax(320px,0.85fr)_minmax(0,1.4fr)]">
      <section id="invoice-preview" className="ds-surface min-h-[320px] overflow-hidden"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex items-center gap-2 font-semibold"><FileText size={18} /> Invoice document</div>{purchase.document ? <Button size="sm" variant="secondary" onClick={() => void downloadInvoice()}><Download size={16} /> Download</Button> : null}</div>{documentUrl ? <iframe className="h-[560px] w-full bg-surface" title="Purchase invoice preview" src={documentUrl} /> : <div className="ds-empty min-h-[260px] text-muted">No invoice document is attached to this purchase.</div>}</section>
      <section className="space-y-5">
        <div className="ds-surface p-5"><h2 className="text-lg font-semibold">Supplier and invoice</h2><div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Supplier" editing={editing}><input className="field-input" value={draft.supplier_name ?? ""} onChange={(event) => updateHeader("supplier_name", event.target.value)} /></Field><Field label="Invoice number" editing={editing}><input className="field-input" value={draft.invoice_number ?? ""} onChange={(event) => updateHeader("invoice_number", event.target.value)} /></Field><Display label="GSTIN" value={purchase.supplier?.gst_number} /><Display label="Contact" value={purchase.supplier?.phone ?? purchase.supplier?.email} /></div></div>
        <div className="ds-surface p-5"><h2 className="text-lg font-semibold">Dates and payment</h2><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><DateField label="Invoice date" value={draft.invoice_date} editing={editing} onChange={(value) => updateHeader("invoice_date", value)} /><DateField label="Purchase date" value={draft.purchase_date} editing={editing} onChange={(value) => updateHeader("purchase_date", value)} /><DateField label="Received date" value={draft.received_date} editing={editing} onChange={(value) => updateHeader("received_date", value)} /><DateField label="Due date" value={draft.due_date} editing={editing} onChange={(value) => updateHeader("due_date", value)} /><Field label="Payment mode" editing={editing}><select className="field-input" value={draft.payment_mode} onChange={(event) => updateHeader("payment_mode", event.target.value)}><option value="CREDIT">Credit</option><option value="CASH">Cash</option><option value="UPI">UPI</option><option value="BANK">Bank transfer</option></select></Field><Field label="Amount paid" editing={editing}><input className="field-input" type="number" min="0" step="0.01" value={draft.amount_paid} onChange={(event) => updateHeader("amount_paid", event.target.value)} /></Field><Field label="Warehouse" editing={editing}><input className="field-input" value={draft.warehouse ?? ""} onChange={(event) => updateHeader("warehouse", event.target.value)} /></Field><Field label="Place of supply" editing={editing}><input className="field-input" value={draft.place_of_supply ?? ""} onChange={(event) => updateHeader("place_of_supply", event.target.value)} /></Field><Field label="Reference" editing={editing}><input className="field-input" value={draft.purchase_reference ?? ""} onChange={(event) => updateHeader("purchase_reference", event.target.value)} /></Field></div><Field label="Notes" editing={editing}><textarea className="field-input h-24 py-3" value={draft.notes ?? ""} onChange={(event) => updateHeader("notes", event.target.value)} /></Field></div>
      </section>
    </div>
    <section className="ds-surface mt-5 overflow-hidden"><div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4"><div><h2 className="text-lg font-semibold">Product items</h2><p className="text-sm text-muted">Quantities and costs remain editable until stock is confirmed.</p></div>{editing ? <Button size="sm" variant="secondary" onClick={() => { setDraft((current) => current ? { ...current, items: [...current.items, blankItem()] } : current); setDirty(true); }}><Plus size={16} /> Add item</Button> : null}</div><div className="overflow-x-auto"><table className="ds-table min-w-[1280px]"><thead><tr><th>#</th><th>Product</th><th>Barcode / SKU</th><th>HSN</th><th>Size</th><th>Colour</th><th className="text-right">Qty</th><th>Unit</th><th className="text-right">Unit cost</th><th className="text-right">Discount</th><th className="text-right">Tax %</th><th className="text-right">Tax</th><th className="text-right">Line total</th><th>Match</th>{editing ? <th /> : null}</tr></thead><tbody>{draft.items.map((item, index) => <tr key={item.id ?? `new-${index}`}><td>{index + 1}</td><ItemInput editing={editing} value={item.product_name} onChange={(value) => updateItem(index, "product_name", value)} /><ItemInput editing={editing} value={item.barcode ?? item.supplier_product_code ?? ""} onChange={(value) => updateItem(index, "barcode", value)} /><ItemInput editing={editing} value={item.hsn_sac ?? ""} onChange={(value) => updateItem(index, "hsn_sac", value)} /><ItemInput editing={editing} value={item.size} onChange={(value) => updateItem(index, "size", value)} /><ItemInput editing={editing} value={item.color} onChange={(value) => updateItem(index, "color", value)} /><ItemInput editing={editing} value={String(item.quantity)} type="number" className="text-right" onChange={(value) => updateItem(index, "quantity", value)} /><ItemInput editing={editing} value={item.unit} onChange={(value) => updateItem(index, "unit", value)} /><ItemInput editing={editing} value={item.purchase_price} type="number" className="text-right" onChange={(value) => updateItem(index, "purchase_price", value)} /><ItemInput editing={editing} value={item.discount} type="number" className="text-right" onChange={(value) => updateItem(index, "discount", value)} /><ItemInput editing={editing} value={item.tax_rate} type="number" className="text-right" onChange={(value) => updateItem(index, "tax_rate", value)} /><ItemInput editing={editing} value={item.tax_amount} type="number" className="text-right" onChange={(value) => updateItem(index, "tax_amount", value)} /><td className="text-right font-semibold">{money(item.line_total)}</td><td><StatusBadge value={item.match_status} /></td>{editing ? <td><Button size="icon" variant="ghost" title="Delete item" aria-label="Delete item" onClick={() => removeItem(index)}><Trash2 size={16} /></Button></td> : null}</tr>)}</tbody></table></div></section>
    <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]"><section className="ds-surface p-5"><h2 className="text-lg font-semibold">AI extraction and inventory impact</h2><div className="mt-4 grid gap-3 sm:grid-cols-2"><Display label="Processing" value={purchase.processing_job?.message ?? purchase.ai_processing_status} /><Display label="Request ID" value={purchase.processing_job?.request_id} /><Display label="Provider" value={purchase.processing_job ? "Configured OCR provider" : "Not available"} /><Display label="Inventory impact" value={purchase.status === "CONFIRMED" ? `${purchase.total_quantity} units added to stock` : "No stock changes until confirmation"} /></div>{purchase.processing_job?.error_message ? <div className="mt-4"><ErrorState message={`${purchase.processing_job.error_message} (${purchase.processing_job.error_code ?? "processing_error"})`} /></div> : null}</section><section className="ds-surface p-5"><h2 className="text-lg font-semibold">Taxes and totals</h2><dl className="mt-4 space-y-3 text-sm"><Total label="Total quantity" value={String(totals.quantity)} /><Total label="Items subtotal" value={money(totals.subtotal)} /><Total label="Discount" value={`-${money(totals.discount)}`} /><Total label="GST / tax" value={money(totals.tax)} /><Total label="Packaging" value={money(draft.packaging_amount)} /><Total label="Freight" value={money(draft.freight_amount)} /><Total label="Round-off" value={money(draft.round_off)} /><div className="border-t border-border pt-3"><Total label="Invoice total" value={money(totals.total)} strong /><Total label="Amount paid" value={money(draft.amount_paid)} /><Total label="Balance due" value={money(totals.total - (Number(draft.amount_paid) || 0))} strong /></div></dl></section></div>
    <section className="ds-surface mt-5 p-5"><h2 className="text-lg font-semibold">Audit history</h2>{purchase.audit_history.length ? <div className="mt-4 divide-y divide-border">{purchase.audit_history.map((audit) => <div key={audit.id} className="py-3"><div className="font-medium">{audit.action.replace(/_/g, " ")}</div><div className="mt-1 text-sm text-muted">{audit.performed_by ?? "System"} · {shortDate(audit.created_at)}{audit.reason ? ` · ${audit.reason}` : ""}</div></div>)}</div> : <p className="mt-3 text-sm text-muted">No changes have been recorded yet.</p>}</section>
    <div className="sticky bottom-3 z-20 mt-6 flex flex-wrap justify-end gap-2 rounded-lg border border-border bg-surface/95 p-3 shadow-lg backdrop-blur">{editing ? <><Button variant="secondary" onClick={discardEdits} disabled={saving}><X size={16} /> Cancel editing</Button><Button variant="secondary" onClick={() => void validatePurchase()} disabled={saving}><ClipboardCheck size={16} /> Validate</Button><Button onClick={() => void save()} disabled={saving}><Save size={16} /> {saving ? "Saving" : "Save draft"}</Button></> : editable ? <><Button variant="secondary" onClick={() => void validatePurchase()}><ClipboardCheck size={16} /> Validate</Button><Button id="cancel-purchase" variant="destructive" onClick={() => setCancelOpen(true)}>Cancel purchase</Button><Button id="confirm-purchase" onClick={() => setConfirmOpen(true)}><CheckCircle2 size={16} /> Confirm and add stock</Button></> : <Button variant="secondary" onClick={() => navigate("/purchases")}><RotateCcw size={16} /> Back to purchases</Button>}</div>
    <ConfirmDialog open={cancelOpen} title="Cancel purchase" description="This cancels the draft without changing stock. Confirmed purchases require the correction workflow." confirmLabel="Cancel purchase" loading={saving} onCancel={() => setCancelOpen(false)} onConfirm={() => void cancelPurchase()}><label className="field-label">Reason<textarea className="field-input h-20 py-2" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} /></label></ConfirmDialog>
    <ConfirmDialog open={confirmOpen} title="Confirm and add stock" description="This action creates purchase inventory movements once and cannot be undone from this page." confirmLabel="Confirm purchase" loading={saving} onCancel={() => setConfirmOpen(false)} onConfirm={() => void confirmPurchase()} />
  </>;
}

function Field({ label, editing, children }: { label: string; editing: boolean; children: React.ReactNode }) { return <label className="field-label">{label}{editing ? children : <span className="min-h-[2.75rem] rounded-lg border border-border bg-surface-subtle px-3.5 py-3 font-normal text-foreground">{children && (children as React.ReactElement).props.value || "-"}</span>}</label>; }
function DateField({ label, value, editing, onChange }: { label: string; value?: string | null; editing: boolean; onChange: (value: string) => void }) { return <label className="field-label">{label}{editing ? <input className="field-input" type="date" value={value ?? ""} onChange={(event) => onChange(event.target.value)} /> : <span className="min-h-[2.75rem] rounded-lg border border-border bg-surface-subtle px-3.5 py-3 font-normal text-foreground">{shortDate(value)}</span>}</label>; }
function Display({ label, value }: { label: string; value?: string | null }) { return <div><dt className="text-xs font-semibold uppercase text-muted">{label}</dt><dd className="mt-1 text-sm text-foreground">{value || "-"}</dd></div>; }
function Total({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) { return <div className={`flex justify-between gap-4 ${strong ? "text-base font-bold text-foreground" : "text-muted"}`}><dt>{label}</dt><dd>{value}</dd></div>; }
function ItemInput({ editing, value, onChange, type = "text", className = "" }: { editing: boolean; value: string; onChange: (value: string) => void; type?: string; className?: string }) { return <td className={className}>{editing ? <input className={`focus-ring h-9 w-28 rounded-md border border-border bg-surface px-2 ${className}`} type={type} min={type === "number" ? "0" : undefined} step={type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} /> : value || "-"}</td>; }

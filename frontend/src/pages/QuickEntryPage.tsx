import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Plus, Save, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { useDraftAttachment } from "../hooks/useDraftAttachment";
import { useDurableDraft } from "../hooks/useDurableDraft";
import { draftKey, prepareSubmission, removeDraft, readDraft } from "../utils/draftStorage";
import type { Product, Purchase, SaleCatalogProduct, SaleCatalogVariant, StockScanSession } from "../types";
import PageHeader from "../components/PageHeader";
import VariantPicker from "../components/VariantPicker";
import Dialog from "../components/Dialog";
import ConfirmDialog from "../components/ConfirmDialog";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { money } from "../utils/format";

export type QuickRow = { product: SaleCatalogProduct; variant: SaleCatalogVariant; quantity: number; cost: string; price: string };
type QuickDraft = { confirming?: boolean; documentId?: string; sessionId: string; version?: number; rows: QuickRow[]; supplierId: string; supplierName: string; date: string; invoice: string; notes: string; payment: string; paid: string; photoName?: string };
function initialDraft(): QuickDraft { return { sessionId: crypto.randomUUID(), rows: [], supplierId: "", supplierName: "Local Wholesale", date: new Date().toLocaleDateString("en-CA"), invoice: "", notes: "", payment: "CASH", paid: "0" }; }
function mergeQuickRow(rows: QuickRow[], next: QuickRow): QuickRow[] {
  const found = rows.some((row) => row.variant.variant_id === next.variant.variant_id);
  return found ? rows.map((row) => row.variant.variant_id === next.variant.variant_id ? { ...next, quantity: row.quantity + next.quantity } : row) : [...rows, next];
}

export default function QuickEntryPage({ purchase = false }: { purchase?: boolean }) {
  const { user } = useAuth(); const queryClient = useQueryClient();
  const key = draftKey(user, purchase ? "quick-purchase" : "quick-stock");
  const [initial] = useState(initialDraft); const { value: draft, setValue: setDraft, saved, clear } = useDurableDraft(key, initial);
  const [resume, setResume] = useState(() => readDraft<QuickDraft>(key, initial).rows.length > 0);
  const [choice, setChoice] = useState<{ product: SaleCatalogProduct; variant: SaleCatalogVariant } | null>(null);
  const [quantity, setQuantity] = useState("1"); const [cost, setCost] = useState(""); const [price, setPrice] = useState("");
  const [busy, setBusy] = useState(false); const inFlight = useRef(false); const [error, setError] = useState(""); const [confirm, setConfirm] = useState(false); const [completed, setCompleted] = useState(false);
  const { file: photo, busy: photoBusy, error: photoError, select: selectPhoto } = useDraftAttachment(`${key}:photo`, purchase);
  const suppliers = useQuery({ queryKey: ["quick-suppliers"], queryFn: () => api.get<Array<{ id: string; name: string }>>("/suppliers"), enabled: purchase });
  const title = purchase ? "Quick Purchase" : "Quick Stock Entry";
  const units = draft.rows.reduce((sum, row) => sum + row.quantity, 0); const total = draft.rows.reduce((sum, row) => sum + Number(row.cost || 0) * row.quantity, 0);
  function update(patch: Partial<QuickDraft>) { if (draft.confirming) return; setDraft((current) => ({ ...current, ...patch })); setCompleted(false); }
  async function choose(product: SaleCatalogProduct, variant: SaleCatalogVariant) {
    if (draft.confirming || busy) return;
    setChoice({ product, variant }); setQuantity("1"); setCost(""); setPrice(variant.selling_price);
    try { const detail = await api.get<Product>(`/products/${product.product_id}`); const exact = detail.variants.find((item) => item.id === variant.variant_id); if (exact) setCost(exact.last_purchase_cost); } catch { /* Cost remains explicitly optional for stock and required for purchase. */ }
  }
  async function sync(current: QuickDraft): Promise<QuickDraft> {
    if (purchase) {
      const payload = { supplier_id: current.supplierId || null, supplier_name: current.supplierName || "Local Wholesale", purchase_date: current.date, invoice_number: current.invoice || null, notes: current.notes || null, payment_mode: current.payment, amount_paid: current.paid || "0", items: current.rows.map((row) => ({ product_variant_id: row.variant.variant_id, quantity: row.quantity, purchase_cost: row.cost || "0", selling_price: row.price || null })) };
      let document: Purchase;
      if (!current.documentId) {
        const submission = prepareSubmission(`${key}:create`, payload);
        document = await api.post<Purchase>("/purchases/quick", submission.payload, { "Idempotency-Key": submission.key });
        current = { ...current, documentId: document.id, version: document.version };
        setDraft(current); removeDraft(`${key}:create`);
        document = await api.put<Purchase>(`/purchases/${document.id}/quick`, { ...payload, version: document.version });
      } else {
        document = await api.get<Purchase>(`/purchases/${current.documentId}`);
        if (document.status === "CONFIRMED") throw new Error("This purchase was already confirmed. Open the purchase history to review it before starting another entry.");
        document = await api.put<Purchase>(`/purchases/${document.id}/quick`, { ...payload, version: current.version ?? document.version });
      }
      current = { ...current, documentId: document.id, version: document.version };
      setDraft(current);
      if (photo) { const form = new FormData(); form.append("file", photo); await api.post(`/purchases/${document.id}/attachment`, form); current = { ...current, photoName: photo.name }; setDraft(current); void selectPhoto(null); }
      return current;
    }
    let session = await api.post<StockScanSession>("/stock-scan/sessions", { session_id: current.sessionId, mode: "DAILY_STOCK", quantity_mode: "QUANTITY_ENTRY", reference: "Daily stock entry" });
    if (session.status === "CONFIRMED") throw new Error("This stock entry was already confirmed. Check stock history before starting another entry.");
    for (const item of session.items.filter((item) => !current.rows.some((row) => row.variant.variant_id === item.product_variant_id))) { await api.delete(`/stock-scan/sessions/${session.id}/items/${item.id}`, { expected_session_updated_at: session.updated_at }); session = await api.get<StockScanSession>(`/stock-scan/sessions/${session.id}`); }
    for (const row of current.rows) session = await api.post<StockScanSession>(`/stock-scan/sessions/${session.id}/quick-items`, { product_variant_id: row.variant.variant_id, quantity: row.quantity, ...(row.cost ? { unit_cost: row.cost } : {}) });
    current = { ...current, documentId: session.id }; setDraft(current); return current;
  }
  async function add() {
    const count = Number(quantity); if (!choice || !Number.isInteger(count) || count < 1 || (purchase && cost === "") || (cost && (!Number.isFinite(Number(cost)) || Number(cost) < 0))) { setError("Enter a whole quantity and a valid purchase cost."); return; }
    const next = { ...draft, rows: mergeQuickRow(draft.rows, { ...choice, quantity: count, cost, price }) }; setDraft(next); setChoice(null); setError(""); setCompleted(false);
    if (inFlight.current) return; inFlight.current = true; setBusy(true);
    try { await sync(next); } catch (cause) { setError(`${cause instanceof Error ? cause.message : "Unable to connect."} Your draft is saved on this device. Try Save again when connected.`); } finally { setBusy(false); inFlight.current = false; }
  }
  async function finish() {
    if (inFlight.current || photoBusy || !draft.rows.length || !saved) return; inFlight.current = true; setBusy(true); setError("");
    try { const current = draft.confirming ? draft : await sync(draft); setDraft({ ...current, confirming: true }); await api.post(purchase ? `/purchases/${current.documentId}/confirm` : `/stock-scan/sessions/${current.documentId}/confirm`, {}); clear(); removeDraft(`${key}:create`); setDraft(initialDraft()); void selectPhoto(null); setCompleted(true); setConfirm(false); for (const query of ["pos-variant-catalog", "products", "inventory-products", "stock-history", "sales-dashboard", "purchases"]) void queryClient.invalidateQueries({ queryKey: [query] }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save. Your draft remains saved; retry this same entry."); }
    finally { inFlight.current = false; setBusy(false); }
  }
  function discard() { if (draft.confirming) return; clear(); removeDraft(`${key}:create`); setDraft(initialDraft()); void selectPhoto(null); setResume(false); }
  return <><PageHeader title={title} subtitle={purchase ? "Add a few wholesale items, then confirm the purchase." : "Choose product and size, enter quantity, then Save Stock."} actions={<Link to={purchase ? "/purchases" : "/stock"} className="inline-flex min-h-11 items-center gap-2 rounded-lg border bg-white px-4 font-semibold"><ArrowLeft size={18} /> Back</Link>} /><div className="mx-auto max-w-5xl space-y-5"><p role="status" className={`rounded-xl border p-4 font-semibold ${saved ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900"}`}>{saved ? "Saved automatically on this device. Inventory changes only after confirmation." : "Draft could not be saved. Keep this page open and free device storage before continuing."}</p>{draft.confirming ? <p role="alert" className="rounded-xl bg-amber-50 p-4">Confirmation is pending. Keep this entry unchanged and press Save again to recover its result.</p> : null}{completed ? <p role="status" className="flex items-center gap-2 rounded-xl bg-emerald-100 p-5 text-lg font-bold text-emerald-950"><CheckCircle2 />{purchase ? "Purchase confirmed." : "Stock saved."} Stock history is updated.</p> : null}{error || photoError ? <ErrorState message={error || photoError} /> : null}{purchase ? <section className="ds-surface grid gap-4 p-5 sm:grid-cols-2"><label className="field-label">Supplier (optional)<select className="field-input" value={draft.supplierId} onChange={(event) => update({ supplierId: event.target.value })}><option value="">Local Wholesale / no supplier</option>{(suppliers.data ?? []).map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select></label><label className="field-label">Date<input type="date" className="field-input" value={draft.date} onChange={(event) => update({ date: event.target.value })} /></label><details className="sm:col-span-2"><summary className="cursor-pointer py-2 font-semibold">Invoice, photo, payment and notes (optional)</summary><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="field-label">Invoice number<input className="field-input" value={draft.invoice} onChange={(event) => update({ invoice: event.target.value })} /></label><label className="field-label">Payment method<select className="field-input" value={draft.payment} onChange={(event) => update({ payment: event.target.value })}>{["CASH", "UPI", "CARD", "BANK", "CREDIT", "OTHER"].map((method) => <option key={method}>{method}</option>)}</select></label><label className="field-label">Amount paid<input type="number" min="0" step="0.01" className="field-input" value={draft.paid} onChange={(event) => update({ paid: event.target.value })} /></label><label className="field-label">Take or upload photo<input type="file" accept="image/*,application/pdf" capture="environment" disabled={busy || draft.confirming || photoBusy} onChange={(event) => void selectPhoto(event.target.files?.[0] ?? null)} /><span className="text-sm text-slate-700">{photo ? `${photo.name} — uploads with the next Save` : draft.photoName || "No photo attached"}</span></label><label className="field-label sm:col-span-2">Notes<textarea className="field-input min-h-20 py-2" value={draft.notes} onChange={(event) => update({ notes: event.target.value })} /></label></div></details></section> : null}<fieldset disabled={busy || draft.confirming} className="min-w-0"><VariantPicker onSelect={(product, variant) => void choose(product, variant)} /></fieldset><section className="ds-surface overflow-hidden"><h2 className="border-b p-4 text-lg font-bold">Your entry · {units} pieces</h2>{draft.rows.length ? draft.rows.map((row) => <div key={row.variant.variant_id} className="flex items-center justify-between gap-3 border-b p-4"><div><strong className="block">{row.product.name}</strong><span className="font-semibold">Size: {row.variant.size || "Standard"}{row.variant.color ? ` · ${row.variant.color}` : ""}</span><p className="text-sm text-slate-700">{row.quantity} pieces{row.cost ? ` · Cost ${money(row.cost)} each` : ""}</p></div><Button type="button" variant="ghost" disabled={busy || draft.confirming} onClick={() => update({ rows: draft.rows.filter((item) => item.variant.variant_id !== row.variant.variant_id) })}><Trash2 size={18} /> Remove</Button></div>) : <p className="p-5 text-slate-700">Choose a product above to begin.</p>}<div className="flex flex-wrap items-center justify-between gap-4 p-4"><div className="font-bold">{units} pieces · Cost {money(total)}</div><Button type="button" className="min-h-12 text-base" disabled={busy || photoBusy || !draft.rows.length || !saved} onClick={() => setConfirm(true)}><Save size={20} />{busy ? "Saving draft…" : purchase ? "Confirm Purchase" : "Save Stock"}</Button></div></section></div><Dialog open={Boolean(choice)} title={choice?.product.name || "Add item"} description={`Size: ${choice?.variant.size || "Standard"}${choice?.variant.color ? ` · ${choice.variant.color}` : ""}`} onClose={() => setChoice(null)}><div className="grid gap-4"><label className="field-label">Quantity<input autoFocus className="field-input text-xl" type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label className="field-label">Purchase cost {purchase ? "per piece" : "(optional)"}<input className="field-input" type="number" min="0" step="0.01" value={cost} onChange={(event) => setCost(event.target.value)} /></label>{purchase ? <label className="field-label">Selling price per piece<input className="field-input" type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></label> : null}<Button type="button" onClick={() => void add()}><Plus size={19} /> Add to draft</Button></div></Dialog><Dialog open={resume} title="You have unfinished stock entry" description="Everything you entered is saved. Continue when you are ready." onClose={() => setResume(false)}><div className="flex flex-wrap gap-3"><Button type="button" onClick={() => setResume(false)}>Continue</Button><Button type="button" variant="secondary" onClick={discard}>Discard draft</Button></div></Dialog><ConfirmDialog open={confirm} title={purchase ? "Confirm this purchase?" : "Save this stock?"} description={`${units} pieces will be added to their selected sizes. ${purchase ? `Purchase cost: ${money(total)}.` : ""}`} confirmLabel={purchase ? "Confirm Purchase" : "Save Stock"} loading={busy} onCancel={() => setConfirm(false)} onConfirm={() => void finish()} /></>;
}

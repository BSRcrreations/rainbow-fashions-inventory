import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, Minus, PackagePlus, Pencil, Plus, ScanLine, Trash2, Volume2, VolumeX } from "lucide-react";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import BarcodeOnboardingDialog from "../components/BarcodeOnboardingDialog";
import { useAuth } from "../hooks/useAuth";
import type { Purchase, StockScanMode, StockScanQuantityMode, StockScanSession } from "../types";
import { money } from "../utils/format";

const modes: Array<{ value: StockScanMode; label: string; description: string }> = [
  { value: "PHYSICAL_COUNT", label: "Physical count", description: "Compare counted pieces with system stock" },
  { value: "OPENING_STOCK", label: "Opening stock", description: "Load original inventory once" },
  { value: "PURCHASE_RECEIVING", label: "Purchase receiving", description: "Review a supplier receipt before purchase confirmation" },
  { value: "STOCK_ADJUSTMENT", label: "Stock adjustment", description: "Record a controlled stock correction" },
  { value: "STOCK_TRANSFER", label: "Stock transfer", description: "Requires location-level inventory" },
];

function modeLabel(mode: StockScanMode) { return modes.find((entry) => entry.value === mode)?.label ?? mode; }
function sessionKey(mode: StockScanMode) { return `rainbow-stock-scan:${mode}`; }
function detailLabel(item: { size?: string | null; color?: string | null; style_code?: string | null; sku?: string | null }) { return [item.size, item.color, item.style_code].filter(Boolean).join(" / ") || item.sku || "Standard"; }

export default function StockScanPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const scannerRef = useRef<HTMLInputElement>(null);
  const lastEvent = useRef<{ value: string; sessionId: string; at: number } | null>(null);
  const requestedSessionMode = useRef<StockScanMode | null>(null);
  const [mode, setMode] = useState<StockScanMode>("OPENING_STOCK");
  const [sessionId, setSessionId] = useState<string>(() => localStorage.getItem(sessionKey("OPENING_STOCK")) ?? "");
  const [barcode, setBarcode] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [quantityMode, setQuantityMode] = useState<StockScanQuantityMode>("INCREMENT");
  const [purchaseId, setPurchaseId] = useState("");
  const [error, setError] = useState("");
  const [latestScan, setLatestScan] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [unknownBarcode, setUnknownBarcode] = useState("");
  const [unknownDialogOpen, setUnknownDialogOpen] = useState(false);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [onboardingAction, setOnboardingAction] = useState<"EXISTING_VARIANT" | "NEW_PRODUCT">("NEW_PRODUCT");
  const [muted, setMuted] = useState(false);

  const sessionQuery = useQuery({
    queryKey: ["stock-scan-session", sessionId],
    queryFn: () => api.get<StockScanSession>(`/stock-scan/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
    retry: false,
  });
  const session = sessionQuery.data;

  const createMutation = useMutation({
    mutationFn: (nextMode: StockScanMode) => api.post<StockScanSession>("/stock-scan/sessions", { mode: nextMode, quantity_mode: quantityMode, purchase_id: nextMode === "PURCHASE_RECEIVING" ? purchaseId : null, location_name: "Main store" }),
    onSuccess: (created) => {
      localStorage.setItem(sessionKey(created.mode), created.id);
      setSessionId(created.id);
      setError("");
      void queryClient.setQueryData(["stock-scan-session", created.id], created);
    },
    onError: (cause) => { requestedSessionMode.current = null; setError(cause instanceof Error ? cause.message : "Unable to start a stock scan session"); },
  });

  useEffect(() => {
    if (!sessionId && !createMutation.isPending && requestedSessionMode.current !== mode && (mode !== "PURCHASE_RECEIVING" || purchaseId)) {
      requestedSessionMode.current = mode;
      createMutation.mutate(mode);
    }
  }, [createMutation, mode, purchaseId, sessionId]);
  useEffect(() => { scannerRef.current?.focus(); }, [sessionId]);

  const scanMutation = useMutation({
    mutationFn: ({ value, count }: { value: string; count: number }) => api.post<StockScanSession>(`/stock-scan/sessions/${sessionId}/scan`, { barcode: value, quantity: count }),
    onSuccess: (next) => {
      void queryClient.setQueryData(["stock-scan-session", next.id], next);
      const item = next.items.find((candidate) => candidate.barcode.toLowerCase() === latestScan.toLowerCase());
      setError("");
      setUnknownBarcode("");
      if (!muted && typeof AudioContext !== "undefined") {
        const audio = new AudioContext(); const tone = audio.createOscillator(); const gain = audio.createGain();
        tone.frequency.value = 760; gain.gain.value = 0.035; tone.connect(gain); gain.connect(audio.destination); tone.start(); tone.stop(audio.currentTime + 0.055);
      }
      toast.success(item ? `${item.product_name}: ${item.scanned_quantity} scanned` : "Barcode added to the count");
    },
    onError: (cause) => {
      const message = cause instanceof Error ? cause.message : "Unable to resolve barcode";
      setError(message);
      if (message.toLowerCase().includes("not assigned") || message.includes("BARCODE_NOT_FOUND")) { setUnknownBarcode(latestScan); setUnknownDialogOpen(true); }
      toast.error(message);
    },
    onSettled: () => { setBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); },
  });

  const itemMutation = useMutation({
    mutationFn: ({ itemId, scanned }: { itemId: string; scanned: number }) => api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}/items/${itemId}`, { scanned_quantity: scanned }),
    onSuccess: (next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to update scan line"; setError(message); toast.error(message); },
  });
  const removeMutation = useMutation({
    mutationFn: (itemId: string) => api.delete(`/stock-scan/sessions/${sessionId}/items/${itemId}`),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["stock-scan-session", sessionId] }); },
    onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to remove scan line"),
  });
  const confirmMutation = useMutation({
    mutationFn: () => api.post<StockScanSession>(`/stock-scan/sessions/${sessionId}/confirm`, {}),
    onSuccess: (next) => {
      void queryClient.setQueryData(["stock-scan-session", next.id], next);
      setConfirmOpen(false); toast.success(`${modeLabel(next.mode)} confirmed. Inventory ledger updated.`);
      for (const key of ["inventory-products", "stock-history", "products", "pos-variant-catalog", "sales-dashboard"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to confirm stock"; setError(message); toast.error(message); },
  });
  const purchasesQuery = useQuery({
    queryKey: ["stock-scan-purchases"],
    queryFn: () => api.get<Purchase[]>("/purchases"),
    enabled: mode === "PURCHASE_RECEIVING" && !sessionId,
  });

  const totals = useMemo(() => {
    const items = session?.items ?? [];
    return { variants: items.length, scans: items.reduce((sum, item) => sum + item.scanned_quantity, 0), pieces: items.reduce((sum, item) => sum + item.base_quantity, 0), positive: items.reduce((sum, item) => sum + Math.max(0, item.difference_quantity ?? 0), 0), negative: items.reduce((sum, item) => sum + Math.abs(Math.min(0, item.difference_quantity ?? 0)), 0) };
  }, [session?.items]);
  const sessionLocked = session?.status === "CONFIRMED";

  function startNewSession() {
    localStorage.removeItem(sessionKey(mode));
    requestedSessionMode.current = null;
    setSessionId("");
    setUnknownDialogOpen(false);
    setOnboardingOpen(false);
    setError("");
  }

  function changeMode(nextMode: StockScanMode) {
    setMode(nextMode); setError(""); setLatestScan(""); setUnknownBarcode(""); setUnknownDialogOpen(false);
    const stored = localStorage.getItem(sessionKey(nextMode));
    requestedSessionMode.current = stored ? nextMode : null;
    setSessionId(stored ?? "");
  }
  function submitScan(value = barcode) {
    const normalized = value.trim();
    if (!normalized || !sessionId || sessionLocked || scanMutation.isPending) return;
    const now = Date.now(); const previous = lastEvent.current;
    if (previous && previous.value === normalized && previous.sessionId === sessionId && now - previous.at < 400) return;
    const parsedQuantity = quantityMode === "INCREMENT" ? 1 : Number(quantity);
    if (!Number.isInteger(parsedQuantity) || parsedQuantity < 1) { setError("Quantity must be a positive whole number"); return; }
    lastEvent.current = { value: normalized, sessionId, at: now }; setLatestScan(normalized); scanMutation.mutate({ value: normalized, count: parsedQuantity });
  }
  function onScannerKeyDown(event: KeyboardEvent<HTMLInputElement>) { if (event.key === "Enter") { event.preventDefault(); submitScan(); } }
  function onSubmit(event: FormEvent) { event.preventDefault(); submitScan(); }
  const canAssign = user?.role === "OWNER" || user?.role === "MANAGER";

  return <>
    <PageHeader title="Scan & Add Stock" subtitle="Scan exact variants, review every package conversion, then confirm one audited inventory change." actions={<Button type="button" variant="secondary" onClick={() => setMuted((value) => !value)} title={muted ? "Enable scan sound" : "Mute scan sound"}>{muted ? <VolumeX size={17} /> : <Volume2 size={17} />}{muted ? "Muted" : "Sound on"}</Button>} />
    <div className="space-y-6">
      <section className="ds-surface p-3 sm:p-4"><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">{modes.map((entry) => <button key={entry.value} type="button" onClick={() => changeMode(entry.value)} className={`rounded-xl border p-3 text-left transition ${mode === entry.value ? "border-primary-500 bg-primary-50 text-primary-800 shadow-sm" : "border-border bg-surface hover:border-primary-300 hover:bg-surface-subtle"}`}><div className="text-sm font-semibold">{entry.label}</div><div className="mt-1 text-xs text-muted">{entry.description}</div></button>)}</div></section>
      {mode === "PURCHASE_RECEIVING" && !sessionId ? <section className="ds-surface flex flex-col gap-3 p-4 sm:flex-row sm:items-end"><label className="field-label flex-1">Purchase to receive<select className="field-input" value={purchaseId} onChange={(event) => setPurchaseId(event.target.value)}><option value="">Select an unconfirmed purchase</option>{(purchasesQuery.data ?? []).filter((purchase) => purchase.status !== "CONFIRMED" && purchase.status !== "CANCELLED" && purchase.status !== "VOIDED").map((purchase) => <option key={purchase.id} value={purchase.id}>{purchase.invoice_number || purchase.purchase_reference || purchase.id} · {purchase.supplier_name || "Supplier pending"}</option>)}</select></label><p className="max-w-md text-sm text-muted">Scanning updates accepted receipt quantities only. Purchase confirmation remains the single action that enters supplier stock.</p></section> : null}
      {mode === "STOCK_TRANSFER" ? <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Transfers are visible here, but cannot be confirmed until location-level inventory is configured. This prevents stock from being moved without a traceable source balance.</div> : null}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="min-w-0 space-y-5">
          <form onSubmit={onSubmit} className="rounded-2xl border border-primary-200 bg-primary-50/60 p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary-700 text-white"><ScanLine size={22} /></div><div className="min-w-0 flex-1"><label className="text-sm font-semibold text-foreground" htmlFor="stock-scan-barcode">Scan barcode and press Enter</label><div className="mt-1 flex gap-2"><input id="stock-scan-barcode" ref={scannerRef} autoFocus disabled={sessionLocked} className="min-w-0 flex-1 border-0 bg-transparent p-0 text-base outline-none placeholder:text-slate-400 disabled:cursor-not-allowed" placeholder="USB, Bluetooth, or manual entry" value={barcode} onChange={(event) => setBarcode(event.target.value)} onKeyDown={onScannerKeyDown} autoComplete="off" /><Button type="submit" disabled={!sessionId || sessionLocked || scanMutation.isPending}>{scanMutation.isPending ? "Scanning" : "Add"}</Button></div><p className="mt-1 text-xs text-muted">{sessionLocked ? "This stock session is confirmed and cannot be changed." : "Focus returns here after every scan. Leading zeros are preserved."}</p></div></div>
            <div className="mt-4 flex flex-col gap-3 border-t border-primary-200/70 pt-4 sm:flex-row sm:items-center sm:justify-between"><div className="inline-flex rounded-lg border border-primary-200 bg-white p-1"><button type="button" disabled={sessionLocked} onClick={() => setQuantityMode("INCREMENT")} className={`rounded-md px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed ${quantityMode === "INCREMENT" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Each scan adds 1</button><button type="button" disabled={sessionLocked} onClick={() => setQuantityMode("QUANTITY_ENTRY")} className={`rounded-md px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed ${quantityMode === "QUANTITY_ENTRY" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Enter quantity after scan</button></div>{quantityMode === "QUANTITY_ENTRY" ? <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">Quantity <input disabled={sessionLocked} className="field-input h-10 w-24" min="1" step="1" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label> : null}</div>
            {latestScan && !error ? <div className="mt-3 flex items-center gap-2 text-sm font-medium text-success"><CheckCircle2 size={17} /> Latest barcode: {latestScan}</div> : null}
            {error ? <div className="mt-3"><ErrorState message={error} /></div> : null}
          </form>
          <section className="ds-surface overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Review scanned variants</h2>
                <p className="mt-1 text-sm text-muted">Review barcode packs and base pieces before confirmation. Inventory stays unchanged until you approve this draft.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{session?.status.replace(/_/g, " ") ?? "Starting session"}</span>
            </div>
            {sessionQuery.isLoading || createMutation.isPending ? <div className="p-6 text-sm text-muted">Preparing your persistent scan session...</div> : sessionQuery.error ? <div className="space-y-3 p-5"><ErrorState message={sessionQuery.error instanceof Error ? sessionQuery.error.message : "Unable to load stock session"} /><Button type="button" variant="secondary" onClick={startNewSession}>Start a new session</Button></div> : session?.items.length ? <div className="overflow-x-auto"><table className="min-w-[1260px] w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3">Product / variant</th><th className="px-4 py-3">SKU / barcode</th><th className="px-4 py-3">MRP</th><th className="px-4 py-3">Current stock</th><th className="px-4 py-3">Scans</th><th className="px-4 py-3">Pack</th><th className="px-4 py-3">Base pieces</th><th className="px-4 py-3">Difference</th><th className="px-4 py-3">Actions</th></tr></thead><tbody className="divide-y divide-border">{session.items.map((item) => <tr key={item.id} className="hover:bg-primary-50/30"><td className="px-4 py-3"><div className="font-semibold text-foreground">{item.product_name}</div><div className="text-xs text-muted">{[item.category_name, item.brand_name, detailLabel(item)].filter(Boolean).join(" · ")}</div></td><td className="px-4 py-3"><div>{item.sku}</div><div className="text-xs text-muted">{item.barcode}</div></td><td className="px-4 py-3">{money(item.mrp ?? item.selling_price)}</td><td className="px-4 py-3 font-medium"><div>{item.current_physical_stock} pieces</div><div className="text-xs text-muted">System count: {item.expected_quantity ?? "-"}</div></td><td className="px-4 py-3"><div className="flex w-32 items-center rounded-lg border border-border bg-surface"><button type="button" disabled={sessionLocked} className="grid h-9 w-9 place-items-center hover:bg-slate-50 disabled:cursor-not-allowed" onClick={() => itemMutation.mutate({ itemId: item.id, scanned: Math.max(0, item.scanned_quantity - 1) })} title="Decrease quantity"><Minus size={15} /></button><input disabled={sessionLocked} aria-label={`Scanned quantity for ${item.product_name}`} className="h-9 w-12 border-x border-border text-center outline-none" value={item.scanned_quantity} type="number" min="0" onChange={(event) => itemMutation.mutate({ itemId: item.id, scanned: Number(event.target.value) || 0 })} /><button type="button" disabled={sessionLocked} className="grid h-9 w-9 place-items-center hover:bg-slate-50 disabled:cursor-not-allowed" onClick={() => itemMutation.mutate({ itemId: item.id, scanned: item.scanned_quantity + 1 })} title="Increase quantity"><Plus size={15} /></button></div></td><td className="px-4 py-3"><div>{item.package_quantity} {item.package_quantity === 1 ? "piece" : "pieces"}</div><div className="text-xs text-muted">per scan</div></td><td className="px-4 py-3 font-semibold text-primary-800">{item.base_quantity} pieces</td><td className={`px-4 py-3 font-bold ${(item.difference_quantity ?? 0) > 0 ? "text-success" : (item.difference_quantity ?? 0) < 0 ? "text-error" : "text-slate-600"}`}>{item.difference_quantity === null || item.difference_quantity === undefined ? "-" : `${item.difference_quantity > 0 ? "+" : ""}${item.difference_quantity}`}</td><td className="px-4 py-3"><button type="button" disabled={sessionLocked} className="focus-ring grid h-9 w-9 place-items-center rounded-lg text-error hover:bg-rose-50 disabled:cursor-not-allowed" onClick={() => removeMutation.mutate(item.id)} title="Remove line" aria-label={`Remove ${item.product_name}`}><Trash2 size={17} /></button></td></tr>)}</tbody></table></div> : <EmptyState icon={ClipboardCheck} title="Ready to count" description="Scan a barcode or type one above. Repeated scans increase one barcode-package review row." />}
          </section>
        </section>
        <aside className="space-y-5 xl:sticky xl:top-20 xl:h-fit"><section className="ds-surface p-5"><h2 className="text-lg font-semibold">Count summary</h2><div className="mt-4 grid grid-cols-2 gap-3"><Summary label="Unique variants" value={totals.variants} /><Summary label="Barcode scans" value={totals.scans} /><Summary label="Base pieces" value={totals.pieces} tone="success" /><Summary label="Negative differences" value={totals.negative} tone="error" /></div><div className="mt-5 space-y-3 border-t border-border pt-4"><label className="field-label">Location<input disabled={sessionLocked} className="field-input" defaultValue={session?.location_name ?? "Main store"} onBlur={(event) => { if (event.target.value.trim() && event.target.value !== session?.location_name) void api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}`, { location_name: event.target.value.trim() }).then((next) => queryClient.setQueryData(["stock-scan-session", next.id], next)).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to update location")); }} /></label><label className="field-label">Reference <span className="!ml-1 !text-xs !font-normal !text-slate-400">Optional</span><input disabled={sessionLocked} className="field-input" defaultValue={session?.reference ?? ""} placeholder="Count sheet or opening reference" onBlur={(event) => { if (event.target.value !== (session?.reference ?? "")) void api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}`, { reference: event.target.value.trim() || null }).then((next) => queryClient.setQueryData(["stock-scan-session", next.id], next)).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to update reference")); }} /></label></div><Button type="button" className="mt-5 w-full" disabled={!session?.items.length || sessionLocked || confirmMutation.isPending || mode === "STOCK_TRANSFER"} onClick={() => setConfirmOpen(true)}><PackagePlus size={18} /> Review and confirm stock</Button>{sessionLocked ? <div className="mt-3 space-y-3"><p className="text-sm font-medium text-success">This stock session is confirmed and cannot be changed.</p><Button type="button" variant="secondary" className="w-full" onClick={startNewSession}>Start new stock session</Button></div> : null}</section><section className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600"><div className="flex items-center gap-2 font-semibold text-slate-800"><Pencil size={16} /> {modeLabel(mode)}</div><p className="mt-2">{mode === "PHYSICAL_COUNT" ? "Confirmation creates count-in or count-out ledger movements. It never overwrites stock." : mode === "OPENING_STOCK" ? "Confirmation creates an OPENING STOCK movement and a cost lot for each added exact variant." : mode === "PURCHASE_RECEIVING" ? "Confirmation records accepted receipt quantities; purchase confirmation remains the only supplier-stock entry point." : "Review the scanned draft before confirmation."}</p></section></aside>
      </div>
    </div>
    <ConfirmDialog open={confirmOpen} title="Confirm stock session" description="This creates append-only inventory movements for every reviewed difference. It cannot be applied twice." confirmLabel="Confirm stock" loading={confirmMutation.isPending} onCancel={() => setConfirmOpen(false)} onConfirm={() => confirmMutation.mutate()}><div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700"><div className="font-semibold">{totals.variants} variants · {totals.pieces} pieces</div>{mode === "PHYSICAL_COUNT" ? <div className="mt-1">{totals.positive} excess and {totals.negative} missing pieces will be recorded as count movements.</div> : null}</div></ConfirmDialog>
    <Dialog open={unknownDialogOpen} onClose={() => { setUnknownDialogOpen(false); setUnknownBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} title="Barcode not registered" description="This barcode is not linked to a product in this store. Nothing has been added to stock.">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><div className="text-xs font-semibold uppercase tracking-wide">Scanned barcode</div><div className="mt-1 font-mono text-base font-bold">{unknownBarcode}</div></div>
      <div className="mt-5 flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" onClick={() => { setUnknownDialogOpen(false); setUnknownBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); }}>Cancel</Button><Button type="button" variant="secondary" onClick={() => { setUnknownDialogOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }}>Scan again</Button>{canAssign ? <><Button type="button" variant="secondary" onClick={() => { setOnboardingAction("EXISTING_VARIANT"); setUnknownDialogOpen(false); setOnboardingOpen(true); }}>Assign existing variant</Button><Button type="button" onClick={() => { setOnboardingAction("NEW_PRODUCT"); setUnknownDialogOpen(false); setOnboardingOpen(true); }}>Create new product</Button></> : <span className="self-center text-sm text-muted">Ask an owner or manager to create the product.</span>}</div>
    </Dialog>
    {session ? <BarcodeOnboardingDialog key={`${session.id}:${unknownBarcode}:${onboardingAction}`} open={onboardingOpen} barcode={unknownBarcode} session={session} initialAction={onboardingAction} initialQuantity={quantityMode === "QUANTITY_ENTRY" ? quantity : "1"} onClose={() => { setOnboardingOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} onSaved={(next, action) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); setOnboardingOpen(false); const assigned = next.items.find((item) => item.barcode.toLowerCase() === unknownBarcode.toLowerCase()); setUnknownBarcode(""); setError(""); toast.success(action === "EXISTING_VARIANT" && assigned ? `Barcode ${assigned.barcode} assigned to ${assigned.product_name} — ${detailLabel(assigned)}.` : `Product created and added to ${modeLabel(mode).toLowerCase()} draft.`); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} /> : null}
  </>;
}

function Summary({ label, value, tone }: { label: string; value: number; tone?: "success" | "error" }) {
  return <div className={`rounded-xl p-3 ${tone === "success" ? "bg-emerald-50" : tone === "error" ? "bg-rose-50" : "bg-slate-50"}`}><div className="text-xs text-muted">{label}</div><div className={`mt-1 text-2xl font-bold ${tone === "success" ? "text-success" : tone === "error" ? "text-error" : "text-foreground"}`}>{value}</div></div>;
}

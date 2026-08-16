import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, Minus, PackagePlus, Pencil, Plus, ScanLine, Trash2, Volume2, VolumeX } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import BarcodeOnboardingDialog from "../components/BarcodeOnboardingDialog";
import BatchBarcodeDialog from "../components/BatchBarcodeDialog";
import BulkBarcodeTransferDialog from "../components/BulkBarcodeTransferDialog";
import ProductFirstStockEntry from "../components/ProductFirstStockEntry";
import type { OnboardingAction } from "../components/barcodeOnboardingLogic";
import { useAuth } from "../hooks/useAuth";
import type { CategoryHierarchy, Product, Purchase, StockHistory, StockScanMode, StockScanQuantityMode, StockScanSession, StockScanSessionItem } from "../types";
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
type SharedBarcodeTarget = { variant_id: string; product_name: string; brand_name?: string | null; size?: string | null; color?: string | null; current_stock: number };

export default function StockScanPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();
  const scannerRef = useRef<HTMLInputElement>(null);
  const lastEvent = useRef<{ value: string; sessionId: string; at: number } | null>(null);
  const requestedSessionMode = useRef<StockScanMode | null>(null);
  const [mode, setMode] = useState<StockScanMode>("OPENING_STOCK");
  const [entryMode, setEntryMode] = useState<"PRODUCT_FIRST" | "BARCODE_FIRST">("PRODUCT_FIRST");
  const [sessionId, setSessionId] = useState<string>(() => localStorage.getItem(sessionKey("OPENING_STOCK")) ?? "");
  const [barcode, setBarcode] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [quantityMode, setQuantityMode] = useState<StockScanQuantityMode>("INCREMENT");
  const [defaultCategoryId, setDefaultCategoryId] = useState<string | null>(null);
  const [defaultBrandId, setDefaultBrandId] = useState<string | null>(null);
  const [purchaseId, setPurchaseId] = useState("");
  const [error, setError] = useState("");
  const [latestScan, setLatestScan] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [unknownBarcode, setUnknownBarcode] = useState("");
  const [unknownDialogOpen, setUnknownDialogOpen] = useState(false);
  const [sharedBarcodeChoice, setSharedBarcodeChoice] = useState<{ barcode: string; targets: SharedBarcodeTarget[] } | null>(null);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [onboardingAction, setOnboardingAction] = useState<OnboardingAction>("NEW_PRODUCT");
  const [muted, setMuted] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const [bulkTransferOpen, setBulkTransferOpen] = useState(false);
  const [correctionItemId, setCorrectionItemId] = useState("");
  const [correctionTarget, setCorrectionTarget] = useState<StockHistory | null>(null);
  const [correctQuantity, setCorrectQuantity] = useState("");
  const [correctionReason, setCorrectionReason] = useState("DATA_ENTRY_MISTAKE");
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [draftEditItem, setDraftEditItem] = useState<StockScanSessionItem | null>(null);
  const [removeItem, setRemoveItem] = useState<StockScanSessionItem | null>(null);

  const sessionQuery = useQuery({
    queryKey: ["stock-scan-session", sessionId],
    queryFn: () => api.get<StockScanSession>(`/stock-scan/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
    retry: false,
  });
  const session = sessionQuery.data;

  const createMutation = useMutation({
    mutationFn: (nextMode: StockScanMode) => api.post<StockScanSession>("/stock-scan/sessions", { mode: nextMode, quantity_mode: quantityMode, purchase_id: nextMode === "PURCHASE_RECEIVING" ? purchaseId : null, default_category_id: (defaultCategoryId ?? "") || null, default_brand_id: (defaultBrandId ?? "") || null, location_name: "Main store" }),
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
      if (cause instanceof ApiError && cause.code === "SHARED_BARCODE_SIZE_REQUIRED") {
        const targets = cause.details?.targets;
        if (Array.isArray(targets)) setSharedBarcodeChoice({ barcode: latestScan, targets: targets as SharedBarcodeTarget[] });
      }
      if (message.toLowerCase().includes("not assigned") || message.includes("BARCODE_NOT_FOUND")) { setUnknownBarcode(latestScan); setUnknownDialogOpen(true); }
      toast.error(message);
    },
    onSettled: () => { setBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); },
  });

  const itemMutation = useMutation({
    mutationFn: ({ itemId, scanned }: { itemId: string; scanned: number }) => api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}/items/${itemId}`, { scanned_quantity: scanned, expected_session_updated_at: session?.updated_at }),
    onSuccess: (next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to update scan line"; setError(message); toast.error(message); },
  });
  const removeMutation = useMutation({
    mutationFn: (itemId: string) => api.delete(`/stock-scan/sessions/${sessionId}/items/${itemId}`, { expected_session_updated_at: session?.updated_at }),
    onSuccess: () => { setRemoveItem(null); void queryClient.invalidateQueries({ queryKey: ["stock-scan-session", sessionId] }); },
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
  const correctionTargetMutation = useMutation({
    mutationFn: (itemId: string) => api.get<StockHistory>(`/stock-scan/sessions/${sessionId}/items/${itemId}/correction-target`),
    onSuccess: (target) => { setCorrectionTarget(target); setCorrectQuantity(String(target.after_stock)); },
    onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to open stock correction"),
  });
  const correctionMutation = useMutation({
    mutationFn: () => { if (!correctionTarget) throw new Error("Select a confirmed stock row"); const amount = Number(correctQuantity); if (!Number.isInteger(amount) || amount < 0) throw new Error("Correct stock must be zero or more"); if (correctionReason === "OTHER" && !correctionNotes.trim()) throw new Error("Notes are required when reason is Other"); return api.post<StockHistory>(`/stock/transactions/${correctionTarget.id}/correct`, { correct_quantity: amount, reason: correctionReason, notes: correctionNotes || null }); },
    onSuccess: () => { toast.success("Original record preserved. The stock correction was recorded."); setCorrectionTarget(null); setCorrectionItemId(""); void queryClient.invalidateQueries({ queryKey: ["inventory-products"] }); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); },
    onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to record stock correction"),
  });
  const purchasesQuery = useQuery({
    queryKey: ["stock-scan-purchases"],
    queryFn: () => api.get<Purchase[]>("/purchases"),
    enabled: mode === "PURCHASE_RECEIVING" && !sessionId,
  });
  const hierarchyQuery = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy") });
  const productsQuery = useQuery({ queryKey: ["stock-draft-products"], queryFn: () => api.get<Product[]>("/products"), enabled: Boolean(draftEditItem) });
  const categories = hierarchyQuery.data ?? [];
  const activeCategoryId = defaultCategoryId ?? session?.default_category_id ?? "";
  const activeBrandId = defaultBrandId ?? session?.default_brand_id ?? "";
  const selectedCategory = categories.find((category) => category.id === activeCategoryId);
  const brands = selectedCategory?.brands.filter((brand) => brand.is_active) ?? [];

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
  function updateSessionDefaults(nextCategoryId: string, nextBrandId: string) {
    setDefaultCategoryId(nextCategoryId);
    setDefaultBrandId(nextBrandId);
    if (sessionId && !sessionLocked) {
      void api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}`, { default_category_id: nextCategoryId || null, default_brand_id: nextBrandId || null }).then((next) => queryClient.setQueryData(["stock-scan-session", next.id], next)).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to update category defaults"));
    }
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
  const canCorrect = canAssign;

  return <>
    <PageHeader title="Scan & Add Stock" subtitle="Scan exact variants, review every package conversion, then confirm one audited inventory change." actions={<Button type="button" variant="secondary" onClick={() => setMuted((value) => !value)} title={muted ? "Enable scan sound" : "Mute scan sound"}>{muted ? <VolumeX size={17} /> : <Volume2 size={17} />}{muted ? "Muted" : "Sound on"}</Button>} />
    <div className="space-y-6">
      {sessionLocked ? <section className="rounded-xl border border-primary-200 bg-primary-50 px-4 py-3"><div className="font-semibold text-primary-950">This stock session is confirmed and cannot be edited.</div><p className="mt-1 text-sm text-primary-900">Use Stock Correction to fix a quantity mistake. The original transaction will remain in the audit history.</p></section> : null}
      <section className="ds-surface p-3 sm:p-4"><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">{modes.map((entry) => <button key={entry.value} type="button" onClick={() => changeMode(entry.value)} className={`rounded-xl border p-3 text-left transition ${mode === entry.value ? "border-primary-500 bg-primary-50 text-primary-800 shadow-sm" : "border-border bg-surface hover:border-primary-300 hover:bg-surface-subtle"}`}><div className="text-sm font-semibold">{entry.label}</div><div className="mt-1 text-xs text-muted">{entry.description}</div></button>)}</div></section>
      <section className="ds-surface flex flex-wrap items-center justify-between gap-3 p-4"><div className="inline-flex rounded-lg border border-primary-200 bg-white p-1"><button type="button" onClick={() => setEntryMode("PRODUCT_FIRST")} className={`rounded-md px-4 py-2 text-sm font-semibold ${entryMode === "PRODUCT_FIRST" ? "bg-primary-700 text-white" : "text-slate-700"}`}>Select Product First</button><button type="button" onClick={() => setEntryMode("BARCODE_FIRST")} className={`rounded-md px-4 py-2 text-sm font-semibold ${entryMode === "BARCODE_FIRST" ? "bg-primary-700 text-white" : "text-slate-700"}`}>Scan Barcode First</button></div><Button type="button" variant="secondary" onClick={startNewSession}>New session</Button></section>
      {entryMode === "BARCODE_FIRST" ? <section className="ds-surface grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:items-end"><label className="field-label">Category filter<select className="field-input mt-1" value={activeCategoryId} onChange={(event) => updateSessionDefaults(event.target.value, "")}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="field-label">Brand filter<select className="field-input mt-1" disabled={!activeCategoryId} value={activeBrandId} onChange={(event) => updateSessionDefaults(activeCategoryId, event.target.value)}><option value="">{activeCategoryId ? "All brands" : "Select category first"}</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label></section> : null}
      {mode === "PURCHASE_RECEIVING" && !sessionId ? <section className="ds-surface flex flex-col gap-3 p-4 sm:flex-row sm:items-end"><label className="field-label flex-1">Purchase to receive<select className="field-input" value={purchaseId} onChange={(event) => setPurchaseId(event.target.value)}><option value="">Select an unconfirmed purchase</option>{(purchasesQuery.data ?? []).filter((purchase) => purchase.status !== "CONFIRMED" && purchase.status !== "CANCELLED" && purchase.status !== "VOIDED").map((purchase) => <option key={purchase.id} value={purchase.id}>{purchase.invoice_number || purchase.purchase_reference || purchase.id} · {purchase.supplier_name || "Supplier pending"}</option>)}</select></label><p className="max-w-md text-sm text-muted">Scanning updates accepted receipt quantities only. Purchase confirmation remains the single action that enters supplier stock.</p></section> : null}
      {mode === "STOCK_TRANSFER" ? <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Transfers are visible here, but cannot be confirmed until location-level inventory is configured. This prevents stock from being moved without a traceable source balance.</div> : null}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="min-w-0 space-y-5">
          {entryMode === "PRODUCT_FIRST" && session ? <ProductFirstStockEntry session={session} canManageCatalog={canAssign} onSaved={(next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); setError(""); }} /> : <form onSubmit={onSubmit} className="rounded-2xl border border-primary-200 bg-primary-50/60 p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary-700 text-white"><ScanLine size={22} /></div><div className="min-w-0 flex-1"><label className="text-sm font-semibold text-foreground" htmlFor="stock-scan-barcode">Scan barcode and press Enter</label><div className="mt-1 flex flex-wrap gap-2"><input id="stock-scan-barcode" ref={scannerRef} autoFocus disabled={sessionLocked} className="min-w-0 flex-1 border-0 bg-transparent p-0 text-base outline-none placeholder:text-slate-400 disabled:cursor-not-allowed" placeholder="USB, Bluetooth, or manual entry" value={barcode} onChange={(event) => setBarcode(event.target.value)} onKeyDown={onScannerKeyDown} autoComplete="off" /><Button type="submit" disabled={!sessionId || sessionLocked || scanMutation.isPending}>{scanMutation.isPending ? "Scanning" : "Add"}</Button>{!sessionLocked && canAssign ? <Button type="button" variant="secondary" onClick={() => setBatchOpen(true)}>Batch scan unique barcodes</Button> : null}{canAssign ? <Button type="button" variant="secondary" onClick={() => setBulkTransferOpen(true)}>Transfer barcodes</Button> : null}</div><p className="mt-1 text-xs text-muted">Focus returns here after every scan. Leading zeros are preserved.</p></div></div>
            {!sessionLocked ? <div className="mt-4 flex flex-col gap-3 border-t border-primary-200/70 pt-4 sm:flex-row sm:items-center sm:justify-between"><div className="inline-flex rounded-lg border border-primary-200 bg-white p-1"><button type="button" onClick={() => setQuantityMode("INCREMENT")} className={`rounded-md px-3 py-2 text-xs font-semibold ${quantityMode === "INCREMENT" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Each scan adds 1</button><button type="button" onClick={() => setQuantityMode("QUANTITY_ENTRY")} className={`rounded-md px-3 py-2 text-xs font-semibold ${quantityMode === "QUANTITY_ENTRY" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Enter quantity after scan</button></div>{quantityMode === "QUANTITY_ENTRY" ? <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">Quantity <input className="field-input h-10 w-24" min="1" step="1" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label> : null}</div> : null}
            {latestScan && !error ? <div className="mt-3 flex items-center gap-2 text-sm font-medium text-success"><CheckCircle2 size={17} /> Latest barcode: {latestScan}</div> : null}
            {error ? <div className="mt-3"><ErrorState message={error} /></div> : null}
          </form>}
          {session?.items.length ? <DraftReview session={session} locked={sessionLocked} onEdit={setDraftEditItem} onQuantity={(itemId, scanned) => itemMutation.mutate({ itemId, scanned })} onRemove={setRemoveItem} /> : session ? <EmptyState icon={ClipboardCheck} title="Ready to count" description="Scan a barcode or select a product to create a non-posting draft row." /> : null}
          <section className="ds-surface hidden overflow-hidden" aria-hidden="true">
            <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Review scanned variants</h2>
                <p className="mt-1 text-sm text-muted">Review barcode packs and base pieces before confirmation. Inventory stays unchanged until you approve this draft.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{session?.status.replace(/_/g, " ") ?? "Starting session"}</span>
            </div>
            {sessionQuery.isLoading || createMutation.isPending ? <div className="p-6 text-sm text-muted">Preparing your persistent scan session...</div> : sessionQuery.error ? <div className="space-y-3 p-5"><ErrorState message={sessionQuery.error instanceof Error ? sessionQuery.error.message : "Unable to load stock session"} /><Button type="button" variant="secondary" onClick={startNewSession}>Start a new session</Button></div> : session?.items.length ? <div className="overflow-x-auto"><table className="min-w-[1260px] w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3">Product / variant</th><th className="px-4 py-3">SKU / barcode</th><th className="px-4 py-3">MRP</th><th className="px-4 py-3">{sessionLocked ? "Confirmed stock" : "Current stock"}</th><th className="px-4 py-3">Scans</th><th className="px-4 py-3">Pack</th><th className="px-4 py-3">Base pieces</th><th className="px-4 py-3">Difference</th><th className="px-4 py-3">Status</th></tr></thead><tbody className="divide-y divide-border">{session.items.map((item) => <tr key={item.id} className="hover:bg-primary-50/30"><td className="px-4 py-3"><div className="font-semibold text-foreground">{item.product_name}</div><div className="text-xs text-muted">{[item.category_name, item.brand_name, detailLabel(item)].filter(Boolean).join(" · ")}</div></td><td className="px-4 py-3"><div>{item.sku}</div><div className="text-xs text-muted">{item.barcode}</div></td><td className="px-4 py-3">{money(item.mrp ?? item.selling_price)}</td><td className="px-4 py-3 font-medium"><div>{item.current_physical_stock} pieces</div><div className="text-xs text-muted">System count: {item.expected_quantity ?? "-"}</div></td><td className="px-4 py-3">{sessionLocked ? <span className="text-sm text-slate-600">Scanned quantity: {item.scanned_quantity}</span> : <div className="flex w-32 items-center rounded-lg border border-border bg-surface"><button type="button" className="grid h-9 w-9 place-items-center hover:bg-slate-50" onClick={() => itemMutation.mutate({ itemId: item.id, scanned: Math.max(0, item.scanned_quantity - 1) })} title="Decrease quantity"><Minus size={15} /></button><input aria-label={`Scanned quantity for ${item.product_name}`} className="h-9 w-12 border-x border-border text-center outline-none" value={item.scanned_quantity} type="number" min="0" onChange={(event) => itemMutation.mutate({ itemId: item.id, scanned: Number(event.target.value) || 0 })} /><button type="button" className="grid h-9 w-9 place-items-center hover:bg-slate-50" onClick={() => itemMutation.mutate({ itemId: item.id, scanned: item.scanned_quantity + 1 })} title="Increase quantity"><Plus size={15} /></button></div>}</td><td className="px-4 py-3"><div>{item.package_quantity} {item.package_quantity === 1 ? "piece" : "pieces"}</div><div className="text-xs text-muted">per scan</div></td><td className="px-4 py-3 font-semibold text-primary-800">{item.base_quantity} pieces</td><td className={`px-4 py-3 font-bold ${(item.difference_quantity ?? 0) > 0 ? "text-success" : (item.difference_quantity ?? 0) < 0 ? "text-error" : "text-slate-600"}`}>{item.difference_quantity === null || item.difference_quantity === undefined ? "-" : `${item.difference_quantity > 0 ? "+" : ""}${item.difference_quantity}`}</td><td className="px-4 py-3">{sessionLocked ? <span className="text-sm font-medium text-slate-500">Confirmed</span> : <button type="button" className="focus-ring grid h-9 w-9 place-items-center rounded-lg text-error hover:bg-rose-50" onClick={() => removeMutation.mutate(item.id)} title="Remove line" aria-label={`Remove ${item.product_name}`}><Trash2 size={17} /></button>}</td></tr>)}</tbody></table></div> : <EmptyState icon={ClipboardCheck} title="Ready to count" description="Scan a barcode or type one above. Repeated scans increase one barcode-package review row." />}
          </section>
        </section>
        <aside className="space-y-5 xl:sticky xl:top-20 xl:h-fit"><section className="ds-surface p-5"><h2 className="text-lg font-semibold">Count summary</h2><div className="mt-4 grid grid-cols-2 gap-3"><Summary label="Unique variants" value={totals.variants} /><Summary label="Barcode scans" value={totals.scans} /><Summary label="Base pieces" value={totals.pieces} tone="success" /><Summary label="Negative differences" value={totals.negative} tone="error" /></div>{sessionLocked ? <div className="mt-5 space-y-2 border-t border-border pt-4"><Button type="button" variant="secondary" className="w-full" onClick={startNewSession}>Start new stock session</Button>{canCorrect ? <Button type="button" className="w-full" disabled={!session?.items.length || correctionTargetMutation.isPending} onClick={() => { const itemId = session?.items[0]?.id; if (itemId) { setCorrectionItemId(itemId); correctionTargetMutation.mutate(itemId); } }}>Correct stock mistake</Button> : null}<Button type="button" variant="secondary" className="w-full" onClick={() => navigate("/stock")}>View inventory history</Button>{canAssign ? <Button type="button" variant="secondary" className="w-full" onClick={() => navigate("/products")}>Manage product</Button> : null}</div> : <><div className="mt-5 space-y-3 border-t border-border pt-4"><label className="field-label">Location<input className="field-input" defaultValue={session?.location_name ?? "Main store"} onBlur={(event) => { if (event.target.value.trim() && event.target.value !== session?.location_name) void api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}`, { location_name: event.target.value.trim() }).then((next) => queryClient.setQueryData(["stock-scan-session", next.id], next)).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to update location")); }} /></label><label className="field-label">Reference <span className="!ml-1 !text-xs !font-normal !text-slate-400">Optional</span><input className="field-input" defaultValue={session?.reference ?? ""} placeholder="Count sheet or opening reference" onBlur={(event) => { if (event.target.value !== (session?.reference ?? "")) void api.patch<StockScanSession>(`/stock-scan/sessions/${sessionId}`, { reference: event.target.value.trim() || null }).then((next) => queryClient.setQueryData(["stock-scan-session", next.id], next)).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to update reference")); }} /></label></div><Button type="button" className="mt-5 w-full" disabled={!session?.items.length || confirmMutation.isPending || mode === "STOCK_TRANSFER"} onClick={() => setConfirmOpen(true)}><PackagePlus size={18} /> Review and confirm stock</Button></>}</section><section className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600"><div className="flex items-center gap-2 font-semibold text-slate-800"><Pencil size={16} /> {modeLabel(mode)}</div><p className="mt-2">{mode === "PHYSICAL_COUNT" ? "Confirmation creates count-in or count-out ledger movements. It never overwrites stock." : mode === "OPENING_STOCK" ? "Confirmation creates an OPENING STOCK movement and a cost lot for each added exact variant." : mode === "PURCHASE_RECEIVING" ? "Confirmation records accepted receipt quantities; purchase confirmation remains the single stock entry point." : "Review the scanned draft before confirmation."}</p></section></aside>
      </div>
    </div>
    <ConfirmDialog open={confirmOpen} title="Confirm stock session" description="This creates append-only inventory movements for every reviewed difference. It cannot be applied twice." confirmLabel="Confirm stock" loading={confirmMutation.isPending} onCancel={() => setConfirmOpen(false)} onConfirm={() => confirmMutation.mutate()}><div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700"><div className="font-semibold">{totals.variants} variants · {totals.pieces} pieces</div>{mode === "PHYSICAL_COUNT" ? <div className="mt-1">{totals.positive} excess and {totals.negative} missing pieces will be recorded as count movements.</div> : null}</div></ConfirmDialog>
    <ConfirmDialog open={Boolean(removeItem)} title="Remove staged item?" description="This removes the row from this draft only. Inventory and cost lots remain unchanged." confirmLabel="Remove item" loading={removeMutation.isPending} onCancel={() => setRemoveItem(null)} onConfirm={() => { if (removeItem) removeMutation.mutate(removeItem.id); }} />
    {session && draftEditItem ? <DraftItemEditor session={session} item={draftEditItem} products={productsQuery.data ?? []} onClose={() => setDraftEditItem(null)} onAddVariant={() => navigate("/products")} onSaved={(next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); setDraftEditItem(null); setError(""); toast.success("Draft row updated. Inventory has not changed."); }} onError={(message) => { setError(message); toast.error(message); }} /> : null}
    <Dialog open={Boolean(correctionTarget)} onClose={() => { setCorrectionTarget(null); setCorrectionItemId(""); }} title="Correct stock mistake" description="The original confirmed transaction will remain in audit history.">{correctionTarget ? <div className="space-y-4"><div className="rounded-lg bg-slate-50 p-3 text-sm"><div className="font-semibold">{session?.items.find((item) => item.id === correctionItemId)?.product_name ?? correctionTarget.product?.name ?? "Product"}</div><div>{session?.items.find((item) => item.id === correctionItemId)?.brand_name || "Unbranded"} · {detailLabel(session?.items.find((item) => item.id === correctionItemId) ?? {})}</div><div>Barcode: {session?.items.find((item) => item.id === correctionItemId)?.barcode ?? "-"}</div><div>Original confirmed quantity: {correctionTarget.qty}</div><div>Current stock: {correctionTarget.after_stock}</div></div><label className="field-label">Correct stock should be<input className="field-input mt-1" min="0" type="number" value={correctQuantity} onChange={(event) => setCorrectQuantity(event.target.value)} /></label><p className="text-sm text-muted">A stock correction of {(Number(correctQuantity || 0) - correctionTarget.after_stock) > 0 ? "+" : ""}{Number(correctQuantity || 0) - correctionTarget.after_stock} will be recorded.</p><label className="field-label">Reason<select className="field-input mt-1" value={correctionReason} onChange={(event) => setCorrectionReason(event.target.value)}><option value="DATA_ENTRY_MISTAKE">Data-entry mistake</option><option value="DUPLICATE_OPENING_STOCK">Duplicate opening stock</option><option value="INCORRECT_VARIANT_SELECTED">Incorrect product selected</option><option value="INCORRECT_BARCODE_ASSIGNMENT">Incorrect barcode assigned</option><option value="TEST_DATA">Test data</option><option value="OTHER">Other</option></select></label><label className="field-label">Notes {correctionReason === "OTHER" ? "(required)" : "(optional)"}<textarea className="field-input mt-1 h-20 py-2" value={correctionNotes} onChange={(event) => setCorrectionNotes(event.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setCorrectionTarget(null)}>Cancel</Button><Button type="button" disabled={correctionMutation.isPending} onClick={() => correctionMutation.mutate()}>{correctionMutation.isPending ? "Recording" : "Record correction"}</Button></div></div> : null}</Dialog>
    <Dialog open={unknownDialogOpen} onClose={() => { setUnknownDialogOpen(false); setUnknownBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} title="Barcode not registered" description="This barcode is not linked to a product in this store. Nothing has been added to stock.">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><div className="text-xs font-semibold uppercase tracking-wide">Scanned barcode</div><div className="mt-1 font-mono text-base font-bold">{unknownBarcode}</div></div>
      <div className="mt-5 flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" onClick={() => { setUnknownDialogOpen(false); setUnknownBarcode(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); }}>Cancel</Button><Button type="button" variant="secondary" onClick={() => { setUnknownDialogOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }}>Scan again</Button>{canAssign ? <><Button type="button" variant="secondary" onClick={() => { setOnboardingAction("EXISTING_VARIANT"); setUnknownDialogOpen(false); setOnboardingOpen(true); }}>Assign existing variant</Button><Button type="button" variant="secondary" onClick={() => { setOnboardingAction("NEW_VARIANT"); setUnknownDialogOpen(false); setOnboardingOpen(true); }}>Create new variant</Button><Button type="button" onClick={() => { setOnboardingAction("NEW_PRODUCT"); setUnknownDialogOpen(false); setOnboardingOpen(true); }}>Create new product</Button></> : <span className="self-center text-sm text-muted">Ask an owner or manager to create the product.</span>}</div>
    </Dialog>
    <Dialog open={Boolean(sharedBarcodeChoice)} onClose={() => setSharedBarcodeChoice(null)} title="Shared barcode detected" description="Choose the exact size before staging stock. Each size keeps independent stock.">{sharedBarcodeChoice ? <div className="space-y-3"><p className="font-mono text-sm">{sharedBarcodeChoice.barcode}</p><div className="grid gap-2 sm:grid-cols-2">{sharedBarcodeChoice.targets.map((target) => <Button key={target.variant_id} type="button" variant="secondary" className="h-auto justify-start py-3 text-left" onClick={() => { const count = quantityMode === "INCREMENT" ? 1 : Number(quantity); if (!Number.isInteger(count) || count < 1) { setError("Quantity must be a positive whole number"); return; } void api.post<StockScanSession>(`/stock-scan/sessions/${sessionId}/stage-variant`, { product_variant_id: target.variant_id, barcode: sharedBarcodeChoice.barcode, quantity: count, confirm_shared_barcode: true }).then((next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); setSharedBarcodeChoice(null); setError(""); toast.success(`${target.product_name} / ${target.size || "Standard"} staged`); }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to stage shared barcode")); }}><span><strong>{target.size || "Standard"}{target.color ? ` · ${target.color}` : ""}</strong><span className="mt-1 block text-xs text-muted">{target.product_name}{target.brand_name ? ` · ${target.brand_name}` : ""} · Stock {target.current_stock}</span></span></Button>)}</div></div> : null}</Dialog>
    {session ? <BarcodeOnboardingDialog key={`${session.id}:${unknownBarcode}:${onboardingAction}`} open={onboardingOpen} barcode={unknownBarcode} session={session} initialAction={onboardingAction} initialQuantity={quantityMode === "QUANTITY_ENTRY" ? quantity : "1"} onClose={() => { setOnboardingOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} onSaved={(next, action) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); setOnboardingOpen(false); const assigned = next.items.find((item) => item.barcode.toLowerCase() === unknownBarcode.toLowerCase()); setUnknownBarcode(""); setError(""); toast.success(action === "EXISTING_VARIANT" && assigned ? `Barcode ${assigned.barcode} assigned to ${assigned.product_name} - ${detailLabel(assigned)}.` : action === "NEW_VARIANT" ? `Variant created and added to ${modeLabel(mode).toLowerCase()} draft.` : `Product created and added to ${modeLabel(mode).toLowerCase()} draft.`); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} /> : null}
    {session ? <BatchBarcodeDialog open={batchOpen} session={session} onClose={() => { setBatchOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} onSaved={(next) => { void queryClient.setQueryData(["stock-scan-session", next.id], next); }} /> : null}
    <BulkBarcodeTransferDialog open={bulkTransferOpen} session={session} onClose={() => { setBulkTransferOpen(false); window.requestAnimationFrame(() => scannerRef.current?.focus()); }} onTransferred={() => { toast.success("Barcode assignments transferred and audited."); if (sessionId) void queryClient.invalidateQueries({ queryKey: ["stock-scan-session", sessionId] }); void queryClient.invalidateQueries({ queryKey: ["inventory-products"] }); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); }} />
  </>;
}

function Summary({ label, value, tone }: { label: string; value: number; tone?: "success" | "error" }) {
  return <div className={`rounded-xl p-3 ${tone === "success" ? "bg-emerald-50" : tone === "error" ? "bg-rose-50" : "bg-slate-50"}`}><div className="text-xs text-muted">{label}</div><div className={`mt-1 text-2xl font-bold ${tone === "success" ? "text-success" : tone === "error" ? "text-error" : "text-foreground"}`}>{value}</div></div>;
}

function DraftReview({ session, locked, onEdit, onQuantity, onRemove }: { session: StockScanSession; locked: boolean; onEdit: (item: StockScanSessionItem) => void; onQuantity: (itemId: string, scanned: number) => void; onRemove: (item: StockScanSessionItem) => void }) {
  return <section className="ds-surface overflow-hidden">
    <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div><h2 className="text-lg font-semibold">Review scanned variants</h2><p className="mt-1 text-sm text-muted">DRAFT — scanning, editing, and removing rows do not change inventory until confirmation.</p></div>
      <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">{locked ? "CONFIRMED" : "DRAFT — NO INVENTORY MOVEMENT"}</span>
    </div>
    <div className="divide-y divide-border">{session.items.map((item) => <article key={item.id} className="grid gap-3 p-4 lg:grid-cols-[minmax(180px,1.7fr)_minmax(110px,0.9fr)_minmax(110px,0.8fr)_minmax(160px,1.15fr)_minmax(185px,1.3fr)] lg:items-center">
      <div><div className="font-semibold text-foreground">{item.product_name}</div><div className="text-xs text-muted">{[item.brand_name, item.category_name].filter(Boolean).join(" · ") || "Unbranded"}</div><div className="mt-1 text-sm font-medium">{detailLabel(item)}</div></div>
      <div><div className="text-xs font-semibold uppercase text-muted">Barcode</div><div className="mt-1 break-all font-mono text-sm">{item.barcode}</div></div>
      <div><div className="text-xs font-semibold uppercase text-muted">Current / adding / after</div><div className="mt-1 font-semibold">{item.current_physical_stock} / {item.base_quantity} / {item.current_physical_stock + (item.difference_quantity ?? item.base_quantity)}</div><div className="text-xs text-muted">{item.package_quantity} per scan</div></div>
      <div>{locked ? <span className="text-sm text-muted">Confirmed quantity: {item.scanned_quantity}</span> : <><label className="text-xs font-semibold uppercase text-muted">Adding</label><div className="mt-1 flex w-32 items-center rounded-lg border border-border bg-surface"><button type="button" className="grid h-9 w-9 place-items-center hover:bg-slate-50" onClick={() => onQuantity(item.id, Math.max(0, item.scanned_quantity - 1))} aria-label={`Decrease ${item.product_name}`}><Minus size={15} /></button><input aria-label={`Scanned quantity for ${item.product_name}`} className="h-9 w-12 border-x border-border text-center outline-none" value={item.scanned_quantity} type="number" min="0" onChange={(event) => onQuantity(item.id, Number(event.target.value) || 0)} /><button type="button" className="grid h-9 w-9 place-items-center hover:bg-slate-50" onClick={() => onQuantity(item.id, item.scanned_quantity + 1)} aria-label={`Increase ${item.product_name}`}><Plus size={15} /></button></div></>}</div>
      <div>{locked ? null : <div className="flex flex-wrap gap-1"><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Edit</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Product</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Variant</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Size</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Colour</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Barcode</Button><Button type="button" size="sm" variant="secondary" onClick={() => onEdit(item)}>Change Quantity</Button><Button type="button" size="sm" variant="secondary" className="text-error" onClick={() => onRemove(item)}>Remove</Button></div>}</div>
    </article>)}</div>
  </section>;
}

function DraftItemEditor({ session, item, products, onClose, onAddVariant, onSaved, onError }: { session: StockScanSession; item: StockScanSessionItem; products: Product[]; onClose: () => void; onAddVariant: () => void; onSaved: (session: StockScanSession) => void; onError: (message: string) => void }) {
  const [productId, setProductId] = useState(item.product_id);
  const [variantId, setVariantId] = useState(item.product_variant_id);
  const [barcode, setBarcode] = useState(item.barcode);
  const [quantity, setQuantity] = useState(String(item.scanned_quantity));
  const [saving, setSaving] = useState(false);
  const selectedProduct = products.find((product) => product.id === productId);
  const selectedVariant = selectedProduct?.variants.find((variant) => variant.id === variantId);
  const categories = [...new Set(products.map((product) => product.category_name || "Uncategorized"))];
  const [category, setCategory] = useState(selectedProduct?.category_name || "");
  const brands = products.filter((product) => !category || (product.category_name || "Uncategorized") === category).map((product) => product.brand_name || "Unbranded");
  const [brand, setBrand] = useState(selectedProduct?.brand_name || "");
  const visibleProducts = products.filter((product) => (!category || (product.category_name || "Uncategorized") === category) && (!brand || (product.brand_name || "Unbranded") === brand));

  async function save(confirmSharedBarcode = false, mergeWithExisting = false) {
    const count = Number(quantity);
    if (!variantId || !Number.isInteger(count) || count < 0 || !barcode.trim()) { onError("Choose an exact variant, enter a barcode, and use a whole-number quantity."); return; }
    setSaving(true);
    try {
      const next = await api.patch<StockScanSession>(`/stock-scan/sessions/${session.id}/items/${item.id}`, { product_variant_id: variantId, barcode: barcode.trim(), scanned_quantity: count, confirm_shared_barcode: confirmSharedBarcode, merge_with_existing: mergeWithExisting, expected_session_updated_at: session.updated_at });
      onSaved(next);
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "SHARED_BARCODE_CONFIRMATION_REQUIRED" && window.confirm("This barcode is shared within the same product and colour. Use it for this exact size?")) { await save(true, false); return; }
      if (cause instanceof ApiError && cause.code === "DRAFT_VARIANT_ALREADY_EXISTS" && window.confirm(`${cause.details?.existing_size || "This variant"} already exists. Use Existing ${cause.details?.existing_size || "variant"} and move this staged quantity?`)) { await save(confirmSharedBarcode, true); return; }
      onError(cause instanceof Error ? cause.message : "Unable to update draft row");
    } finally { setSaving(false); }
  }

  return <Dialog open onClose={onClose} title="Edit staged stock" description="This is a draft correction. Inventory, ledger movements, and cost lots remain unchanged until final confirmation.">
    <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><label className="field-label">Category<select className="field-input mt-1" value={category} onChange={(event) => { setCategory(event.target.value); setBrand(""); setProductId(""); setVariantId(""); }}><option value="">All categories</option>{categories.map((entry) => <option key={entry} value={entry}>{entry}</option>)}</select></label><label className="field-label">Brand<select className="field-input mt-1" value={brand} onChange={(event) => { setBrand(event.target.value); setProductId(""); setVariantId(""); }}><option value="">All brands</option>{[...new Set(brands)].map((entry) => <option key={entry} value={entry}>{entry}</option>)}</select></label></div><label className="field-label">Product<select className="field-input mt-1" value={productId} onChange={(event) => { setProductId(event.target.value); setVariantId(visibleProducts.find((product) => product.id === event.target.value)?.variants[0]?.id || ""); }}><option value="">Select product</option>{visibleProducts.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label><label className="field-label">Exact variant — size / colour<select className="field-input mt-1" value={variantId} onChange={(event) => setVariantId(event.target.value)}><option value="">Select variant</option>{selectedProduct?.variants.filter((variant) => variant.is_active).map((variant) => <option key={variant.id} value={variant.id}>{[variant.size || "Standard", variant.color, variant.style_code].filter(Boolean).join(" · ")}</option>)}</select></label><div className="flex items-center justify-between gap-3"><p className="text-xs text-muted">Create a new exact size or colour with the existing safe workflow; it starts at zero stock.</p><Button type="button" size="sm" variant="secondary" onClick={onAddVariant}>+ Add Variant</Button></div><div className="grid gap-3 sm:grid-cols-2"><label className="field-label">Barcode<input className="field-input mt-1" value={barcode} onChange={(event) => setBarcode(event.target.value)} /></label><label className="field-label">Quantity<input className="field-input mt-1" min="0" step="1" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label></div>{selectedVariant ? <div className="rounded-lg bg-slate-50 p-3 text-sm"><strong>{selectedVariant.current_stock} current</strong> · Adding {Number(quantity) || 0} · After confirmation {selectedVariant.current_stock + (Number(quantity) || 0)}</div> : null}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="button" disabled={saving} onClick={() => void save()}>{saving ? "Saving" : "Save draft correction"}</Button></div></div>
  </Dialog>;
}

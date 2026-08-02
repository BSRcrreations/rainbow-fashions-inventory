import { FormEvent, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { ApiError, api } from "../api/client";
import type { SaleCatalogProduct, SaleCatalogVariant, StockScanSession } from "../types";
import Dialog from "./Dialog";
import ErrorState from "./ErrorState";
import { Button } from "./ui/button";

interface Props { open: boolean; session: StockScanSession; onClose: () => void; onSaved: (session: StockScanSession) => void; }
type Selection = { product: SaleCatalogProduct; variant: SaleCatalogVariant };
const variantLabel = (variant: SaleCatalogVariant) => [variant.size, variant.color, variant.style_code].filter(Boolean).join(" / ") || variant.sku;

export default function BatchBarcodeDialog({ open, session, onClose, onSaved }: Props) {
  const scannerRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [barcode, setBarcode] = useState("");
  const [paste, setPaste] = useState("");
  const [conflicts, setConflicts] = useState(0);
  const [expectedPieces, setExpectedPieces] = useState("");
  const [error, setError] = useState("");
  const catalog = useQuery({ queryKey: ["batch-barcode-catalog", search], enabled: open && !selection, queryFn: () => api.get<SaleCatalogProduct[]>(`/sales/catalog${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`) });
  const parsedPaste = useMemo(() => paste.split(/\r?\n/).map((value) => value.trim()).filter((value) => value && value.toLowerCase() !== "barcode"), [paste]);
  const selectedItems = useMemo(() => selection ? session.items.filter((item) => item.product_variant_id === selection.variant.variant_id) : [], [selection, session.items]);
  const scannedPieces = selectedItems.reduce((total, item) => total + item.scanned_quantity, 0);
  const distinctVariants = new Set(selectedItems.map((item) => item.product_variant_id)).size;
  const batch = useMutation({
    mutationFn: (barcodes: string[]) => {
      if (!selection) throw new Error("Select the exact variant first");
      return api.post<StockScanSession>(`/stock-scan/sessions/${session.id}/batch-barcodes`, { product_variant_id: selection.variant.variant_id, barcodes });
    },
    onSuccess: (next) => { onSaved(next); setBarcode(""); setPaste(""); setError(""); window.requestAnimationFrame(() => scannerRef.current?.focus()); },
    onError: (cause) => { if (cause instanceof ApiError && cause.code === "BARCODE_VARIANT_CONFLICT") setConflicts((current) => current + 1); setError(cause instanceof Error ? cause.message : "Unable to assign batch barcode"); },
  });
  const remove = useMutation({ mutationFn: async (itemId: string) => { await api.delete(`/stock-scan/sessions/${session.id}/items/${itemId}`); return api.get<StockScanSession>(`/stock-scan/sessions/${session.id}`); }, onSuccess: (next) => { onSaved(next); window.requestAnimationFrame(() => scannerRef.current?.focus()); }, onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to remove batch barcode") });
  function scan(event: FormEvent) { event.preventDefault(); const value = barcode.trim(); if (!value || batch.isPending) return; batch.mutate([value]); }
  return <Dialog open={open} onClose={onClose} title="Batch scan product barcode" description="Repeated manufacturer-barcode scans increase the staged quantity for the selected exact variant." maxWidth="xl">
    {!selection ? <section className="space-y-3">
      <label className="field-label">Find category, brand, product, or exact variant<div className="relative mt-1"><Search size={16} className="absolute left-3 top-3 text-muted" /><input autoFocus className="field-input pl-9" placeholder="Search product, brand, SKU, size, or colour" value={search} onChange={(event) => setSearch(event.target.value)} /></div></label>
      <div className="max-h-80 space-y-2 overflow-y-auto">{(catalog.data ?? []).map((product) => <div key={product.product_id} className="rounded-lg border border-border p-3"><div className="font-semibold">{product.name}</div><div className="text-xs text-muted">{product.category_name} · {product.brand_name}</div><div className="mt-2 grid gap-2 sm:grid-cols-2">{product.variants.filter((variant) => variant.is_active).map((variant) => <button key={variant.variant_id} type="button" className="rounded-md border border-border p-2 text-left text-sm hover:border-primary-400 hover:bg-primary-50" onClick={() => setSelection({ product, variant })}><div className="font-semibold">{variantLabel(variant)}</div><div className="text-xs text-muted">{variant.sku} · {variant.available_stock} in stock</div></button>)}</div></div>)}</div>
    </section> : <section className="space-y-4">
      <div className="rounded-xl border border-primary-200 bg-primary-50 p-4"><div className="text-xs font-semibold uppercase tracking-wide text-primary-700">Selected exact variant</div><div className="mt-1 font-semibold">{selection.product.name}</div><div className="text-sm text-primary-900">{selection.product.brand_name} · {variantLabel(selection.variant)}</div><div className="mt-1 text-xs text-primary-800">SKU: {selection.variant.sku} · MRP: {selection.variant.mrp ?? "-"} · Selling price: {selection.variant.selling_price} · Current stock: {selection.variant.available_stock}</div><p className="mt-2 text-sm text-primary-900">Manufacturer barcodes map to this exact variant. Scan the same barcode for every physical piece.</p><div className="mt-3 flex gap-2"><Button type="button" variant="secondary" size="sm" onClick={() => { setSelection(null); setConflicts(0); }}>Change variant</Button><Button type="button" variant="secondary" size="sm" disabled={!selectedItems.length || remove.isPending} onClick={() => Promise.all(selectedItems.map((item) => remove.mutateAsync(item.id)))}>Clear batch</Button></div></div>
      <form onSubmit={scan} className="flex gap-2"><input ref={scannerRef} autoFocus className="field-input flex-1" placeholder="Scan manufacturer barcode and press Enter" value={barcode} onChange={(event) => setBarcode(event.target.value)} /><Button type="submit" disabled={batch.isPending}>{batch.isPending ? "Adding" : "Add scan"}</Button></form>
      <label className="field-label">Expected pieces <span className="text-muted">optional</span><input className="field-input mt-1" min="1" type="number" value={expectedPieces} onChange={(event) => setExpectedPieces(event.target.value)} /></label>
      <label className="field-label">Paste or CSV import<textarea className="field-input mt-1 h-24 py-2" placeholder={"barcode\n8906058070526\n8906058070526"} value={paste} onChange={(event) => setPaste(event.target.value)} /></label>
      <Button type="button" variant="secondary" disabled={!parsedPaste.length || batch.isPending} onClick={() => batch.mutate(parsedPaste)}>Add {parsedPaste.length} scan{parsedPaste.length === 1 ? "" : "s"}</Button>
      <div className="text-sm text-muted">Scanned pieces: {scannedPieces}{expectedPieces ? ` of ${expectedPieces}` : ""} · Distinct variants: {distinctVariants} · Conflicts: {conflicts} · Errors: {error ? 1 : 0}</div>
      {expectedPieces && scannedPieces === Number(expectedPieces) ? <p className="text-sm font-medium text-success">Expected quantity reached.</p> : null}
      {error ? <ErrorState message={error} /> : null}
      {selectedItems.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2">Product / variant</th><th>Barcode</th><th>Quantity</th><th>Status</th><th>Action</th></tr></thead><tbody>{selectedItems.map((item) => <tr key={item.id} className="border-t border-border"><td className="py-2"><div className="font-medium">{item.product_name}</div><div className="text-xs text-muted">{item.brand_name} · {[item.size, item.color, item.style_code].filter(Boolean).join(" / ")}</div></td><td className="font-mono">{item.barcode}</td><td className="font-semibold">{item.scanned_quantity}</td><td className="text-success">Staged</td><td><Button type="button" size="sm" variant="secondary" disabled={remove.isPending} onClick={() => remove.mutate(item.id)}>Remove row</Button></td></tr>)}</tbody></table></div> : null}
    </section>}
    <div className="mt-5 flex justify-end"><Button type="button" variant="secondary" onClick={onClose}>{selection ? "Finish batch" : "Cancel"}</Button></div>
  </Dialog>;
}

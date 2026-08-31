import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, CheckCircle2, Eye, ShieldAlert } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "./ErrorState";
import { useToast } from "./ToastProvider";
import { Button } from "./ui/button";
import { useAuth } from "../hooks/useAuth";
import type { Product, VariantCorrectionPreview, VariantCorrectionReason, VariantCorrectionResult } from "../types";

type CorrectionPayload = {
  source_variant_id: string;
  destination_variant_id: string;
  quantity: number;
  reason: VariantCorrectionReason;
  notes?: string;
};

const reasons: Array<{ value: VariantCorrectionReason; label: string }> = [
  { value: "WRONG_SIZE_ENTERED", label: "Wrong size entered" },
  { value: "INCORRECT_VARIANT_SELECTED", label: "Incorrect variant selected" },
  { value: "INCORRECT_BARCODE_ASSIGNMENT", label: "Incorrect barcode assignment" },
  { value: "DATA_ENTRY_MISTAKE", label: "Data entry mistake" },
  { value: "TEST_DATA", label: "Test data" },
  { value: "OTHER", label: "Other" },
];

function variantLabel(product: Product, variant: Product["variants"][number]) {
  return `${product.name} / ${variant.size || "Standard"}${variant.color ? ` / ${variant.color}` : ""} / ${variant.internal_sku} / ${variant.current_stock} in stock`;
}

export default function VariantCorrectionPanel({ products }: { products: Product[] }) {
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [sourceId, setSourceId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState<VariantCorrectionReason>("WRONG_SIZE_ENTERED");
  const [notes, setNotes] = useState("");
  const [preview, setPreview] = useState<VariantCorrectionPreview | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [error, setError] = useState("");
  const source = useMemo(() => products.flatMap((product) => product.variants.map((variant) => ({ product, variant }))).find((row) => row.variant.id === sourceId) ?? null, [products, sourceId]);
  const destinations = useMemo(() => source ? (source.product.variants ?? []).filter((variant) => variant.id !== source.variant.id && variant.is_active) : [], [source]);

  function payload(): CorrectionPayload {
    const pieces = Number(quantity);
    if (!sourceId || !destinationId) throw new Error("Select both source and destination variants");
    if (!Number.isInteger(pieces) || pieces <= 0) throw new Error("Quantity must be a whole number greater than zero");
    if (reason === "OTHER" && !notes.trim()) throw new Error("Add notes when the reason is Other");
    return { source_variant_id: sourceId, destination_variant_id: destinationId, quantity: pieces, reason, notes: notes.trim() || undefined };
  }

  function changeSelection(change: () => void) {
    change(); setPreview(null); setError(""); setIdempotencyKey(crypto.randomUUID());
  }

  const previewMutation = useMutation({
    mutationFn: () => api.post<VariantCorrectionPreview>("/stock/variant-corrections/preview", payload()),
    onSuccess: (result) => { setPreview(result); setError(""); },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to preview correction"),
  });
  const confirmMutation = useMutation({
    mutationFn: () => api.post<VariantCorrectionResult>("/stock/variant-corrections", payload(), { "Idempotency-Key": idempotencyKey }),
    onSuccess: (result) => {
      toast.success(result.already_completed ? "This correction was already recorded" : "Variant correction recorded");
      setPreview(null); setSourceId(""); setDestinationId(""); setQuantity("1"); setNotes(""); setError(""); setIdempotencyKey(crypto.randomUUID());
      for (const key of ["inventory-products", "adjustment-products", "stock-history", "products", "pos-variant-catalog", "sales-dashboard"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to record correction"),
  });

  if (user?.role !== "OWNER" && user?.role !== "MANAGER") return null;
  return <section className="mb-6 rounded-lg border border-violet-200 bg-white p-5 shadow-sm sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900"><ArrowRightLeft size={20} /> Correct Variant / Move Stock</h2><p className="mt-1 max-w-3xl text-sm text-slate-600">Use only when confirmed stock was recorded against the wrong size or variant. This appends matching stock movements; it never edits the product, variants, barcode values, or existing history.</p></div><a className="btn-secondary" href="/products">Create missing variant first</a></div>
    <div className="mt-5 grid gap-4 lg:grid-cols-2"><label className="field-label">Source variant (stock recorded here)<span>*</span><select className="field-input mt-1" value={sourceId} onChange={(event) => changeSelection(() => { setSourceId(event.target.value); setDestinationId(""); })}><option value="">Select source variant</option>{products.flatMap((product) => (product.variants ?? []).filter((variant) => variant.is_active).map((variant) => <option key={variant.id} value={variant.id}>{variantLabel(product, variant)}</option>))}</select></label><label className="field-label">Destination variant (stock belongs here)<span>*</span><select className="field-input mt-1" value={destinationId} disabled={!source} onChange={(event) => changeSelection(() => setDestinationId(event.target.value))}><option value="">{source ? "Select destination variant" : "Choose source first"}</option>{source ? destinations.map((variant) => <option key={variant.id} value={variant.id}>{variantLabel(source.product, variant)}</option>) : null}</select></label><label className="field-label">Quantity to move<span>*</span><input className="field-input mt-1" type="number" min="1" step="1" value={quantity} onChange={(event) => changeSelection(() => setQuantity(event.target.value))} /></label><label className="field-label">Correction reason<span>*</span><select className="field-input mt-1" value={reason} onChange={(event) => changeSelection(() => setReason(event.target.value as VariantCorrectionReason))}>{reasons.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></div>
    <label className="field-label mt-4">Notes {reason === "OTHER" ? <span>*</span> : <span className="text-slate-400">(optional)</span>}<textarea className="field-input mt-1 min-h-20" value={notes} onChange={(event) => changeSelection(() => setNotes(event.target.value))} placeholder="Why the stock was recorded against the wrong variant" /></label>
    {source ? <p className="mt-3 text-sm text-slate-600">Available in source: <strong>{source.variant.current_stock}</strong> pieces. Destinations are restricted to variants of <strong>{source.product.name}</strong>.</p> : null}
    {error ? <div className="mt-4"><ErrorState message={error} /></div> : null}
    <div className="mt-5 flex flex-wrap gap-3 border-t border-slate-100 pt-5"><Button type="button" variant="secondary" disabled={previewMutation.isPending || confirmMutation.isPending} onClick={() => previewMutation.mutate()}><Eye size={17} /> {previewMutation.isPending ? "Previewing" : "Preview — no stock changes"}</Button>{preview ? <Button type="button" disabled={confirmMutation.isPending} onClick={() => confirmMutation.mutate()}><CheckCircle2 size={17} /> {confirmMutation.isPending ? "Recording correction" : "Confirm correction"}</Button> : null}</div>
    {preview ? <div className="mt-5 rounded-lg border border-violet-200 bg-violet-50 p-4"><div className="flex items-center gap-2 font-semibold text-violet-950"><ShieldAlert size={18} /> Preview only — stock has not changed</div><div className="mt-3 grid gap-3 md:grid-cols-2"><div className="rounded bg-white p-3 text-sm"><div className="font-semibold">Source: {preview.source.size || "Standard"}{preview.source.color ? ` / ${preview.source.color}` : ""}</div><div>{preview.source.before_stock} → <strong>{preview.source.after_stock}</strong> pieces</div><div className="text-slate-500">SKU {preview.source.sku}</div></div><div className="rounded bg-white p-3 text-sm"><div className="font-semibold">Destination: {preview.destination.size || "Standard"}{preview.destination.color ? ` / ${preview.destination.color}` : ""}</div><div>{preview.destination.before_stock} → <strong>{preview.destination.after_stock}</strong> pieces</div><div className="text-slate-500">SKU {preview.destination.sku}</div></div></div><p className="mt-3 text-sm text-violet-950">Confirming will append two linked audit movements with reference {preview.reference}.</p></div> : null}
  </section>;
}

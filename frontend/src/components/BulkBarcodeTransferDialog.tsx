import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, Search } from "lucide-react";
import { api } from "../api/client";
import type { BulkBarcodeTransferPreview, SaleCatalogProduct, StockScanSession } from "../types";
import Dialog from "./Dialog";
import ErrorState from "./ErrorState";
import { Button } from "./ui/button";
import { barcodeTransferErrorMessage, canConfirmBarcodeTransfer, hasDuplicateBarcodes, parseTransferBarcodes, variantTransferLabel } from "./barcodeTransferLogic";

interface Props {
  open: boolean;
  onClose: () => void;
  onTransferred: (result: BulkBarcodeTransferPreview) => void;
  session?: StockScanSession | null;
}

const defaultReason = "Incorrect size assignment: M to S";

export default function BulkBarcodeTransferDialog({ open, onClose, onTransferred, session }: Props) {
  const [barcodeText, setBarcodeText] = useState("8903289095861\n8903289095502\n8903289118621\n8903289110502");
  const [search, setSearch] = useState("Twin birds ankle");
  const [targetVariantId, setTargetVariantId] = useState("");
  const [reason, setReason] = useState(defaultReason);
  const [confirmation, setConfirmation] = useState("");
  const [preview, setPreview] = useState<BulkBarcodeTransferPreview | null>(null);
  const [error, setError] = useState("");

  const barcodes = useMemo(() => parseTransferBarcodes(barcodeText), [barcodeText]);
  const catalog = useQuery({
    queryKey: ["barcode-transfer-catalog", search],
    enabled: open,
    queryFn: () => api.get<SaleCatalogProduct[]>(`/sales/catalog${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`),
  });

  const previewMutation = useMutation({
    mutationFn: () => {
      if (!barcodes.length) throw new Error("Enter at least one barcode.");
      if (hasDuplicateBarcodes(barcodes)) throw new Error("Remove duplicate barcode values.");
      if (!targetVariantId) throw new Error("Select the exact target S variant.");
      return api.post<BulkBarcodeTransferPreview>("/barcodes/bulk-transfer/preview", { barcodes, target_product_variant_id: targetVariantId, reason });
    },
    onSuccess: (next) => {
      setPreview(next);
      setConfirmation("");
      setError("");
    },
    onError: (cause) => setError(barcodeTransferErrorMessage(cause)),
  });

  const transferMutation = useMutation({
    mutationFn: () => {
      if (!preview) throw new Error("Preview this transfer first.");
      if (!canConfirmBarcodeTransfer(confirmation, preview.confirmation_phrase)) throw new Error(`Type ${preview.confirmation_phrase} to confirm this transfer.`);
      return api.post<BulkBarcodeTransferPreview>("/barcodes/bulk-transfer", {
        barcodes: preview.barcodes,
        target_product_variant_id: preview.target.variant_id,
        reason,
        confirmation_phrase: confirmation,
      });
    },
    onSuccess: (result) => {
      onTransferred(result);
      setPreview(result);
      setError("");
    },
    onError: (cause) => setError(barcodeTransferErrorMessage(cause)),
  });

  return (
    <Dialog open={open} onClose={onClose} title="Transfer barcode assignments" description="Move physical-piece barcodes to the exact correct variant with preview and audit." maxWidth="xl">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,420px)]">
        <div className="space-y-4">
          <label className="field-label">
            Barcodes
            <textarea className="field-input mt-1 h-32 py-2 font-mono" value={barcodeText} onChange={(event) => { setBarcodeText(event.target.value); setPreview(null); }} />
          </label>
          <label className="field-label">
            Reason
            <input className="field-input mt-1" value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
          <label className="field-label">
            Search target product
            <div className="relative mt-1">
              <Search size={16} className="absolute left-3 top-3 text-muted" />
              <input className="field-input pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Product, brand, size, barcode, SKU" />
            </div>
          </label>
          <div className="max-h-72 space-y-2 overflow-y-auto rounded-lg border border-border p-2">
            {(catalog.data ?? []).map((product) => (
              <div key={product.product_id} className="rounded-md border border-border p-3">
                <div className="font-semibold">{product.name}</div>
                <div className="text-xs text-muted">{[product.brand_name, product.category_name].filter(Boolean).join(" · ")}</div>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {product.variants.map((variant) => (
                    <button key={variant.variant_id} type="button" onClick={() => { setTargetVariantId(variant.variant_id); setPreview(null); }} className={`rounded-md border px-2 py-2 text-left text-xs ${targetVariantId === variant.variant_id ? "border-primary-500 bg-primary-50" : "border-border hover:bg-slate-50"}`}>
                      <div className="font-semibold">{variantTransferLabel(variant)}</div>
                      <div>{variant.sku} · {variant.available_stock} in stock</div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-border bg-slate-50 p-4 text-sm">
            <div className="font-semibold">Transfer preview</div>
            <div className="mt-2">{barcodes.length} barcode{barcodes.length === 1 ? "" : "s"} selected</div>
            {session ? <div className="text-xs text-muted">Current draft: {session.items.length} row{session.items.length === 1 ? "" : "s"}</div> : null}
          </div>
          {error ? <ErrorState message={error} /> : null}
          {preview ? (
            <div className="space-y-3 rounded-lg border border-primary-200 bg-primary-50 p-4 text-sm text-primary-950">
              <div className="font-semibold">Move {preview.barcodes.length} barcodes?</div>
              <div>
                <div className="text-xs font-semibold uppercase text-primary-700">From</div>
                <div>{preview.source.product_name}</div>
                <div>{preview.source.brand_name || "Unbranded"} · {variantTransferLabel(preview.source)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-primary-700">To</div>
                <div>{preview.target.product_name}</div>
                <div>{preview.target.brand_name || "Unbranded"} · {variantTransferLabel(preview.target)}</div>
              </div>
              <div className="rounded-md bg-white p-2 font-mono text-xs">{preview.barcodes.map((item) => <div key={item}>{item}</div>)}</div>
              <div>
                <div className="font-semibold">Stock impact</div>
                {preview.draft_only ? <div>No confirmed stock change</div> : <div>{variantTransferLabel(preview.source)}: {preview.source_stock_delta} · {variantTransferLabel(preview.target)}: +{preview.target_stock_delta} · Net: {preview.net_stock_delta}</div>}
              </div>
              <label className="field-label">
                Type {preview.confirmation_phrase}
                <input className="field-input mt-1" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
              </label>
            </div>
          ) : null}
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
            <Button type="button" variant="secondary" disabled={previewMutation.isPending} onClick={() => previewMutation.mutate()}>{previewMutation.isPending ? "Previewing" : "Preview transfer"}</Button>
            <Button type="button" disabled={!preview || !canConfirmBarcodeTransfer(confirmation, preview.confirmation_phrase) || transferMutation.isPending} onClick={() => transferMutation.mutate()}>
              <ArrowRightLeft size={17} /> {transferMutation.isPending ? "Transferring" : "Confirm barcode transfer"}
            </Button>
          </div>
        </aside>
      </div>
    </Dialog>
  );
}

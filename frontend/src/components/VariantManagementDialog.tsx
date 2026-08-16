import { FormEvent, useState } from "react";
import { Archive, RotateCcw, Trash2 } from "lucide-react";
import { api } from "../api/client";
import type { Product, ProductVariant } from "../types";
import Dialog from "./Dialog";
import { useToast } from "./ToastProvider";
import { Button } from "./ui/button";

interface Props {
  open: boolean;
  product: Product;
  variant: ProductVariant;
  canPermanentlyDelete: boolean;
  onClose: () => void;
  onSaved: () => void;
  onEditProduct: () => void;
}

type DeleteCheck = { can_delete: boolean; reason?: string | null; references: Record<string, number> };

export default function VariantManagementDialog({ open, product, variant, canPermanentlyDelete, onClose, onSaved, onEditProduct }: Props) {
  const toast = useToast();
  const [size, setSize] = useState(variant.size ?? "");
  const [color, setColor] = useState(variant.color ?? "");
  const [styleCode, setStyleCode] = useState(variant.style_code ?? "");
  const [manufacturerSku, setManufacturerSku] = useState(variant.manufacturer_sku ?? "");
  const [mrp, setMrp] = useState(variant.mrp ?? "");
  const [sellingPrice, setSellingPrice] = useState(variant.selling_price);
  const [purchaseCost, setPurchaseCost] = useState(variant.last_purchase_cost);
  const [sku, setSku] = useState(variant.internal_sku);
  const [barcode, setBarcode] = useState(variant.barcode);
  const [scanUnit, setScanUnit] = useState<"PIECE" | "PACK">(variant.scan_unit ?? "PIECE");
  const [piecesPerPack, setPiecesPerPack] = useState(String(variant.pieces_per_pack ?? 1));
  const [pending, setPending] = useState(false);
  const [deleteCheck, setDeleteCheck] = useState<DeleteCheck | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true); setError("");
    try {
      await api.patch(`/product-variants/${variant.id}`, { size: size || null, color: color || null, style_code: styleCode || null, manufacturer_sku: manufacturerSku || null, mrp: mrp || null, selling_price: sellingPrice, purchase_cost: purchaseCost, internal_sku: sku, barcode, scan_unit: scanUnit, pieces_per_pack: scanUnit === "PACK" ? Number(piecesPerPack) : 1 });
      toast.success("Variant updated"); onSaved(); onClose();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to update variant"); }
    finally { setPending(false); }
  }

  async function archive(active: boolean) {
    setPending(true); setError("");
    try { await api.post(`/product-variants/${variant.id}/${active ? "restore" : "archive"}`); toast.success(active ? "Variant restored" : "Variant archived"); onSaved(); onClose(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to change variant status"); }
    finally { setPending(false); }
  }

  async function openDelete() {
    setPending(true); setError("");
    try { setDeleteCheck(await api.get<DeleteCheck>(`/product-variants/${variant.id}/deletion-check`)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to check deletion eligibility"); }
    finally { setPending(false); }
  }

  async function destroy() {
    setPending(true); setError("");
    try { await api.delete(`/product-variants/${variant.id}`, { confirmation }); toast.success("Variant permanently deleted"); onSaved(); onClose(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to delete variant"); }
    finally { setPending(false); }
  }

  return <Dialog open={open} title="EDIT VARIANT" description="Changes apply only to this variant. Scanning or selecting loaded these values; nothing is saved until Save Changes." onClose={onClose} maxWidth="lg">
    <form className="space-y-5" onSubmit={submit}>
      <section className="rounded-lg border border-line bg-slate-50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Product</p><p className="font-semibold text-slate-950">{product.name}</p><p className="mt-1 text-sm text-slate-600">{product.brand?.name || "Unbranded"} · {product.category?.name || "Uncategorised"}</p></div><Button type="button" variant="secondary" size="sm" onClick={onEditProduct}>Edit product</Button></div></section>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">Size<input className="field-input mt-1" value={size} onChange={(event) => setSize(event.target.value)} /></label>
        <label className="field-label">Colour<input className="field-input mt-1" value={color} onChange={(event) => setColor(event.target.value)} /></label>
        <label className="field-label">Style / model<input className="field-input mt-1" value={styleCode} onChange={(event) => setStyleCode(event.target.value)} /></label>
        <label className="field-label">Manufacturer SKU<input className="field-input mt-1" value={manufacturerSku} onChange={(event) => setManufacturerSku(event.target.value)} /></label>
        <label className="field-label">MRP<input className="field-input mt-1" type="number" min="0" step="0.01" value={mrp} onChange={(event) => setMrp(event.target.value)} /></label>
        <label className="field-label">Selling price<input className="field-input mt-1" required type="number" min="0" step="0.01" value={sellingPrice} onChange={(event) => setSellingPrice(event.target.value)} /></label>
        <label className="field-label">Purchase cost<input className="field-input mt-1" required type="number" min="0" step="0.01" value={purchaseCost} onChange={(event) => setPurchaseCost(event.target.value)} /></label>
        <label className="field-label">SKU<input className="field-input mt-1" required value={sku} onChange={(event) => setSku(event.target.value)} /></label>
        <label className="field-label sm:col-span-2">Barcode<input className="field-input mt-1 font-mono" required value={barcode} onChange={(event) => setBarcode(event.target.value)} /></label>
      </div>
      <section className="rounded-lg border border-line bg-slate-50 p-4"><h3 className="font-semibold text-slate-900">Scan method</h3><div className="mt-3 grid gap-4 sm:grid-cols-2"><label className="field-label">Scan as<select className="field-input mt-1" value={scanUnit} onChange={(event) => setScanUnit(event.target.value as "PIECE" | "PACK")}><option value="PIECE">Piece</option><option value="PACK">Pack</option></select></label>{scanUnit === "PACK" ? <label className="field-label">Pieces per pack<input className="field-input mt-1" required type="number" min="2" value={piecesPerPack} onChange={(event) => setPiecesPerPack(event.target.value)} /></label> : <p className="self-end text-sm text-slate-600">Inventory stays in individual pieces.</p>}</div><p className="mt-3 text-xs text-slate-500">Future scans use this conversion; previously staged scans keep their recorded package quantity.</p></section>
      {error ? <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
      {deleteCheck ? <section className={`rounded-lg border p-4 ${deleteCheck.can_delete ? "border-rose-200 bg-rose-50" : "border-amber-200 bg-amber-50"}`}><h3 className="font-semibold">{deleteCheck.can_delete ? "Permanent deletion available" : "Permanent deletion blocked"}</h3><p className="mt-1 text-sm">{deleteCheck.can_delete ? "This variant has zero stock and no dependent records." : deleteCheck.reason}</p>{deleteCheck.can_delete ? <><label className="field-label mt-3">Type DELETE VARIANT to continue<input className="field-input mt-1" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label><div className="mt-3 flex justify-end"><Button type="button" variant="destructive" disabled={pending || confirmation !== "DELETE VARIANT"} onClick={() => void destroy()}><Trash2 size={15} /> Permanently delete variant</Button></div></> : <p className="mt-3 text-sm font-medium">Archive this variant instead; its ID, barcode mapping, and history will remain available.</p>}</section> : null}
      <section className="rounded-lg border border-teal-100 bg-teal-50/50 p-3 text-sm text-teal-950"><strong>Current stock: {variant.current_stock}</strong><p className="mt-1">Managed through Stock Adjustment. This form cannot change stock.</p></section>
      <div className="flex flex-wrap justify-between gap-2 border-t border-line pt-4"><div className="flex gap-2">{variant.is_active ? <Button type="button" variant="secondary" disabled={pending} onClick={() => void archive(false)}><Archive size={15} /> Archive</Button> : <Button type="button" variant="secondary" disabled={pending} onClick={() => void archive(true)}><RotateCcw size={15} /> Restore</Button>}{canPermanentlyDelete ? <Button type="button" variant="ghost" className="text-rose-700" disabled={pending} onClick={() => void openDelete()}><Trash2 size={15} /> Delete</Button> : null}</div><div className="flex gap-2"><Button type="button" variant="secondary" onClick={onClose} disabled={pending}>Cancel</Button><Button type="submit" disabled={pending}>{pending ? "Saving" : "Save variant"}</Button></div></div>
    </form>
  </Dialog>;
}

import { useEffect, useRef, useState } from "react";
import JsBarcode from "jsbarcode";
import Dialog from "./Dialog";
import { Button } from "./ui/button";
import ErrorState from "./ErrorState";
import type { Product } from "../types";
import { money } from "../utils/format";
import { useStoreSettings } from "../hooks/useStoreSettings";
import { printDocument } from "../utils/printing";

export default function BarcodeLabelDialog({ open, product, onClose }: { open: boolean; product: Product | null; onClose: () => void }) {
  const settings = useStoreSettings(); const label = settings.data?.label; const svg = useRef<SVGSVGElement>(null); const preview = useRef<HTMLDivElement>(null);
  const [copies, setCopies] = useState<number | null>(null); const [variantId, setVariantId] = useState(""); const [error, setError] = useState("");
  const variants = product?.variants ?? []; const variant = variants.find((item) => item.id === variantId) ?? (variants.length === 1 ? variants[0] : undefined);
  const barcode = variant?.barcode ?? (variants.length ? "" : product?.barcode ?? "");
  useEffect(() => { if (!open || !svg.current || !barcode) return; try { JsBarcode(svg.current, barcode, { format: "CODE128", displayValue: false, height: 34, margin: 0, width: 1.4 }); } catch { /* Invalid external codes are rejected on printing below. */ } }, [barcode, open, label]);
  function print() { if (!preview.current || !label || !barcode) return; try { if (svg.current) JsBarcode(svg.current, barcode, { format: "CODE128", displayValue: false, height: 34, margin: 0, width: 1.4 }); printDocument(preview.current.innerHTML, label.width_mm, label.margin_mm, copies ?? label.copies, label.height_mm); setError(""); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not print this barcode."); } }
  return <Dialog open={open} title="Print barcode labels" description={label ? `${label.width_mm} × ${label.height_mm} mm labels` : "Loading label settings…"} onClose={onClose} maxWidth="md"><div className="space-y-4">{settings.error ? <ErrorState message="Could not load printer settings." /> : null}{variants.length > 1 ? <label className="field-label">Choose size / colour<select className="field-input" value={variant?.id ?? ""} onChange={(event) => setVariantId(event.target.value)}><option value="">Choose the exact item</option>{variants.map((item) => <option key={item.id} value={item.id}>{[item.size, item.color, item.internal_sku].filter(Boolean).join(" · ")}</option>)}</select></label> : null}{barcode && product && label ? <><div ref={preview} className="mx-auto border bg-white p-2 text-black" style={{ width: `${label.width_mm}mm`, minHeight: `${label.height_mm}mm`, maxWidth: "100%" }}><div className="label-meta">{settings.data?.name}</div>{label.show_product_name && <div className="label-name">{product.name}</div>}{label.show_size && <div className="label-meta">{[variant?.size ?? product.size, variant?.color ?? product.color].filter(Boolean).join(" · ")}</div>}<svg ref={svg} className="barcode" style={{ width: "100%", height: "9mm" }} aria-label={`Barcode ${barcode}`} />{label.show_barcode_number && <div className="label-code">{barcode}</div>}{label.show_mrp && <div className="label-meta">MRP {money(variant?.mrp ?? product.mrp ?? product.selling_price)}</div>}</div><label className="field-label">Copies<input className="field-input" type="number" min="1" max="100" value={copies ?? label.copies} onChange={(event) => setCopies(Math.min(100, Math.max(1, Number(event.target.value) || 1)))} /></label><Button type="button" onClick={print}>Print labels</Button></> : <p>Choose an item with a barcode before printing.</p>}{error && <ErrorState message={error} />}</div></Dialog>;
}

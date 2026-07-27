import { useEffect, useRef, useState } from "react";
import JsBarcode from "jsbarcode";
import { Printer } from "lucide-react";
import Dialog from "./Dialog";
import { Button } from "./ui/button";
import type { Product } from "../types";
import { money, shortDate } from "../utils/format";

interface BarcodeLabelDialogProps {
  open: boolean;
  product: Product | null;
  onClose: () => void;
}

function escapeHtml(value: string) {
  return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ?? character);
}

export default function BarcodeLabelDialog({ open, product, onClose }: BarcodeLabelDialogProps) {
  const barcodeRef = useRef<SVGSVGElement>(null);
  const [copies, setCopies] = useState(1);
  const barcode = product?.barcode ?? "";

  useEffect(() => {
    if (!open || !barcodeRef.current || !barcode) return;
    JsBarcode(barcodeRef.current, barcode, {
      format: "CODE128",
      displayValue: false,
      height: 34,
      margin: 0,
      width: 1.45,
    });
  }, [barcode, open]);

  function printLabels() {
    if (!product || !barcodeRef.current || !barcode) return;
    const printWindow = window.open("", "barcode-labels", "noopener,noreferrer,width=600,height=500");
    if (!printWindow) return;
    const label = `<article class="label"><div class="name">${escapeHtml(product.name)}</div><div class="meta">${escapeHtml([product.size, product.color].filter(Boolean).join(" · ") || "Standard")}</div><svg class="barcode" viewBox="${barcodeRef.current.getAttribute("viewBox") ?? "0 0 1 1"}" xmlns="http://www.w3.org/2000/svg">${barcodeRef.current.innerHTML}</svg><div class="code">${escapeHtml(barcode)}</div><div class="details"><span>${escapeHtml(shortDate(product.product_date))}</span><strong>${escapeHtml(money(product.selling_price))}</strong></div></article>`;
    printWindow.document.write(`<!doctype html><html><head><title>Barcode labels</title><style>@page { size: 50mm 30mm; margin: 0; } * { box-sizing: border-box; } body { margin: 0; font-family: Arial, sans-serif; } .label { width: 50mm; height: 30mm; padding: 2.2mm; overflow: hidden; page-break-after: always; color: #111827; } .name { font-size: 10pt; line-height: 1.15; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .meta { margin-top: .5mm; font-size: 7pt; color: #475569; } .barcode { display: block; width: 45.6mm; height: 10mm; margin: 1.2mm 0 .2mm; } .code { font-family: monospace; font-size: 7pt; text-align: center; letter-spacing: .35mm; } .details { display: flex; justify-content: space-between; margin-top: 1mm; font-size: 7pt; }</style></head><body>${label.repeat(copies)}</body></html>`);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  }

  return <Dialog open={open} title="Print barcode labels" description="50 mm × 30 mm retail labels" onClose={onClose} maxWidth="md">
    {product && barcode ? <div className="space-y-5"><div className="mx-auto w-[50mm] rounded border border-border bg-white p-[2.2mm] text-foreground shadow-sm"><div className="truncate text-sm font-bold">{product.name}</div><div className="mt-0.5 text-[11px] text-muted">{[product.size, product.color].filter(Boolean).join(" · ") || "Standard"}</div><svg ref={barcodeRef} className="mt-2 h-[10mm] w-full" aria-label={`Barcode ${barcode}`} role="img" /><div className="font-mono text-center text-[11px] tracking-[0.15em]">{barcode}</div><div className="mt-1 flex justify-between text-[10px]"><span>{shortDate(product.product_date)}</span><strong>{money(product.selling_price)}</strong></div></div><label className="field-label">Label copies<input className="field-input" type="number" min="1" max="100" value={copies} onChange={(event) => setCopies(Math.min(100, Math.max(1, Number(event.target.value) || 1)))} /></label><Button type="button" className="w-full" onClick={printLabels}><Printer size={17} /> Print {copies} {copies === 1 ? "label" : "labels"}</Button></div> : <p className="text-sm text-muted">This product needs a barcode before it can be printed.</p>}
  </Dialog>;
}

import { printDocument } from "../utils/printing";
import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Printer, Save } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { useAuth } from "../hooks/useAuth";
import { useStoreSettings, type StoreSettings } from "../hooks/useStoreSettings";

export default function PrinterSettingsPage() {
  const query = useStoreSettings(); const { user } = useAuth();
  return <><PageHeader title="Printer Settings" subtitle="Set up a receipt printer and a separate barcode label printer." />{query.error ? <ErrorState message={query.error.message} /> : query.data ? <PrinterForm key={query.dataUpdatedAt} initial={query.data} editable={user?.role === "OWNER" || user?.role === "MANAGER"} /> : <p role="status">Loading printers…</p>}</>;
}

function PrinterForm({ initial, editable }: { initial: StoreSettings; editable: boolean }) {
  const [receipt, setReceipt] = useState(initial.receipt); const [label, setLabel] = useState(initial.label);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [saved, setSaved] = useState(false); const client = useQueryClient();
  function testPrint(kind: "receipt" | "label") { try { const config = kind === "receipt" ? receipt : label; printDocument("<h2>Rainbow Fashions</h2><p>PRINTER TEST ONLY</p><hr /><p>1234567890 • ₹ 123.45</p><p>Check paper width and alignment.</p>", config.width_mm, config.margin_mm, 1, kind === "label" ? label.height_mm : undefined); } catch (cause) { setError(cause instanceof Error ? cause.message : "Printing failed."); } }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { const result = await api.put<StoreSettings>("/settings/printers", { receipt, label }); client.setQueryData(["store-settings"], result); setSaved(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save printer settings."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={(event) => void save(event)} className="space-y-5">
    {error && <ErrorState message={error} />}{saved && <p role="status" className="rounded-lg bg-emerald-50 p-4 font-semibold text-emerald-900">Printer settings saved.</p>}
    <p className="rounded-lg bg-blue-50 p-4 text-blue-950">Use the browser Print window to choose the connected printer. Paper size, density and device options are also available in your printer driver.</p>
    <fieldset disabled={!editable || busy} className="grid gap-5 lg:grid-cols-2">
      <section className="ds-surface space-y-5 p-5"><h2 className="flex items-center gap-3 text-xl font-bold"><Printer />Receipt Printer</h2>
        <p>Standard browser / system printing</p>
        <label className="field-label">Receipt width<select className="field-input" value={receipt.width_mm} onChange={(e) => setReceipt({ ...receipt, width_mm: Number(e.target.value) as 80 | 58 })}><option value={80}>80 mm thermal receipt</option><option value={58}>58 mm thermal receipt</option></select></label>
        <label className="field-label">Margin (mm)<input className="field-input" type="number" min="0" max="10" step="0.5" value={receipt.margin_mm} onChange={(e) => setReceipt({ ...receipt, margin_mm: Number(e.target.value) })} /></label>
        <label className="field-label">Receipt copies<input className="field-input" type="number" min="1" max="5" value={receipt.copies} onChange={(e) => setReceipt({ ...receipt, copies: Number(e.target.value) })} /></label>
        <label className="flex min-h-12 items-center gap-3"><input type="checkbox" className="h-5 w-5" checked={receipt.show_gst} onChange={(e) => setReceipt({ ...receipt, show_gst: e.target.checked })} />Show recorded GST details</label>
        <label className="field-label">Tax calculation for new bills<select className="field-input" value={receipt.tax_mode ?? "INTRA_STATE"} onChange={(e) => setReceipt({ ...receipt, tax_mode: e.target.value as "INTRA_STATE" | "INTER_STATE" })}><option value="INTRA_STATE">CGST + SGST</option><option value="INTER_STATE">IGST</option></select></label><label className="field-label">Return / exchange policy<textarea className="field-input" maxLength={300} value={receipt.return_policy} onChange={(e) => setReceipt({ ...receipt, return_policy: e.target.value })} /></label>
        <label className="field-label">Thank-you message<input className="field-input" maxLength={180} value={receipt.thank_you} onChange={(e) => setReceipt({ ...receipt, thank_you: e.target.value })} /></label>
      </section>
      <section className="ds-surface space-y-5 p-5"><h2 className="flex items-center gap-3 text-xl font-bold"><Printer />Label Printer</h2>
        <p>Works with any printer supported by this device.</p>
        <label className="field-label">Common label sizes<select className="field-input" value={`${label.width_mm}x${label.height_mm}`} onChange={(e) => { const [width_mm, height_mm] = e.target.value.split("x").map(Number); setLabel({ ...label, width_mm, height_mm }); }}><option value="50x30">50 × 30 mm</option><option value="40x30">40 × 30 mm</option><option value="40x20">40 × 20 mm</option>{!["50x30", "40x30", "40x20"].includes(`${label.width_mm}x${label.height_mm}`) && <option value={`${label.width_mm}x${label.height_mm}`}>Custom size</option>}</select></label>
        <div className="grid grid-cols-2 gap-3"><label className="field-label">Width (mm)<input className="field-input" type="number" min="20" max="120" value={label.width_mm} onChange={(e) => setLabel({ ...label, width_mm: Number(e.target.value) })} /></label><label className="field-label">Height (mm)<input className="field-input" type="number" min="15" max="100" value={label.height_mm} onChange={(e) => setLabel({ ...label, height_mm: Number(e.target.value) })} /></label></div>
        <label className="field-label">Margin (mm)<input className="field-input" type="number" min="0" max="8" step="0.5" value={label.margin_mm} onChange={(e) => setLabel({ ...label, margin_mm: Number(e.target.value) })} /></label>
        <label className="field-label">Default copies<input className="field-input" type="number" min="1" max="100" value={label.copies} onChange={(e) => setLabel({ ...label, copies: Number(e.target.value) })} /></label>
        {([["show_product_name", "Product name"], ["show_size", "Size / colour"], ["show_mrp", "MRP"], ["show_barcode_number", "Barcode number"]] as const).map(([key, title]) => <label key={key} className="flex min-h-12 items-center gap-3"><input type="checkbox" className="h-5 w-5" checked={label[key]} onChange={(e) => setLabel({ ...label, [key]: e.target.checked })} />{title}</label>)}
      </section>
    </fieldset>
    <div className="flex flex-wrap gap-3"><Button type="button" variant="secondary" onClick={() => testPrint("receipt")}>Print test receipt</Button><Button type="button" variant="secondary" onClick={() => testPrint("label")}>Print test label</Button></div>
    {editable && <div className="flex justify-end gap-3"><Button type="button" variant="secondary" disabled={busy} onClick={() => { setReceipt(initial.receipt); setLabel(initial.label); }}>Cancel changes</Button><Button type="submit" disabled={busy}><Save size={19} />{busy ? "Saving…" : "Save Printer Settings"}</Button></div>}
  </form>;
}

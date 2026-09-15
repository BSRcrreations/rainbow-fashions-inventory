import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { useAuth } from "../hooks/useAuth";
import { useStoreSettings, type StoreSettings } from "../hooks/useStoreSettings";

export default function StoreSettingsPage() {
  const query = useStoreSettings();
  const { user } = useAuth();
  return <><PageHeader title="Store Settings" subtitle="Your shop details appear on printed bills." />{query.error ? <ErrorState message={query.error.message} /> : query.data ? <SettingsForm key={query.dataUpdatedAt} initial={query.data} editable={user?.role === "OWNER"} /> : <p role="status">Loading shop settings…</p>}</>;
}

function SettingsForm({ initial, editable }: { initial: StoreSettings; editable: boolean }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const client = useQueryClient();
  function field(key: keyof StoreSettings, value: unknown) { setForm({ ...form, [key]: value }); setSaved(false); }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { const result = await api.put<StoreSettings>("/settings/store", form); client.setQueryData(["store-settings"], result); setSaved(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save shop settings."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={(event) => void save(event)} className="ds-surface mx-auto max-w-3xl space-y-5 p-5 sm:p-7">
    {error && <ErrorState message={error} />}{saved && <p role="status" className="rounded-lg bg-emerald-50 p-4 font-semibold text-emerald-900">Shop settings saved.</p>}
    <fieldset disabled={!editable || busy} className="grid gap-5 sm:grid-cols-2">
      <label className="field-label sm:col-span-2">Shop name<input className="field-input" required minLength={2} maxLength={120} value={form.name} onChange={(e) => field("name", e.target.value)} /></label>
      <label className="field-label sm:col-span-2">Address<textarea className="field-input" maxLength={500} rows={3} value={form.address} onChange={(e) => field("address", e.target.value)} /></label>
      <label className="field-label">Phone<input className="field-input" type="tel" maxLength={30} value={form.phone} onChange={(e) => field("phone", e.target.value)} /></label>
      <label className="field-label">GSTIN (optional)<input className="field-input" maxLength={40} value={form.gstin} onChange={(e) => field("gstin", e.target.value)} /></label>
      <label className="field-label">Cashier discount limit (%)<input className="field-input" type="number" min="0" max="100" step="0.01" required value={form.cashier_max_discount_percent} onChange={(e) => field("cashier_max_discount_percent", e.target.value)} /><span className="text-sm font-normal">Higher discounts require a manager.</span></label>
      <label className="flex min-h-12 items-center gap-3"><input type="checkbox" className="h-5 w-5" checked={form.require_payment_reference} onChange={(e) => field("require_payment_reference", e.target.checked)} />Require reference for electronic payments</label>
      <details className="sm:col-span-2"><summary className="cursor-pointer py-3 font-semibold">Advanced shop settings</summary><div className="mt-3 grid gap-4"><label className="field-label">Time zone<input className="field-input" value={form.timezone} onChange={(e) => field("timezone", e.target.value)} /><span className="text-sm font-normal">India: Asia/Kolkata. This controls day closing dates.</span></label><label className="field-label">Uploaded logo path<input className="field-input" placeholder="/uploads/products/your-logo.png" value={form.logo_url} onChange={(e) => field("logo_url", e.target.value)} /></label></div></details>
    </fieldset>
    {editable ? <div className="flex flex-wrap justify-end gap-3"><Button type="button" variant="secondary" disabled={busy} onClick={() => { setForm(initial); setSaved(false); }}>Cancel changes</Button><Button type="submit" disabled={busy}><Save size={19} />{busy ? "Saving…" : "Save Settings"}</Button></div> : <p>Ask the owner to change shop details.</p>}
  </form>;
}

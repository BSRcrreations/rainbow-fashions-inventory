import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, Save } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { useAuth } from "../hooks/useAuth";
import { money } from "../utils/format";

type ClosingSummary = { business_date: string; timezone: string; opening_cash: string; cash_sales: string; cash_refunds: string; cash_expenses: string; customer_cash_payments: string; supplier_cash_payments?: string; expected_cash: string; payment_totals: Record<string, string>; bills: number };
type Closing = { id: string; business_date: string; opening_cash: string; actual_cash: string; expected_cash: string; difference: string; status: string; notes?: string; summary_json: ClosingSummary };
const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());

export default function DayClosingPage() {
  const { user } = useAuth(); const client = useQueryClient();
  const [day, setDay] = useState(today); const [opening, setOpening] = useState("0"); const [actual, setActual] = useState(""); const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [saved, setSaved] = useState(""); const [skip, setSkip] = useState(0);
  const canSubmit = ["OWNER", "MANAGER", "CASHIER", "STAFF"].includes(user?.role ?? "");
  const canApprove = user?.role === "OWNER" || user?.role === "MANAGER";
  const preview = useQuery({ queryKey: ["day-closing-preview", day, opening], queryFn: () => api.get<ClosingSummary>(`/day-closing/preview?business_date=${day}&opening_cash=${Number(opening) || 0}`), enabled: canSubmit && Boolean(day) && Number(opening) >= 0 });
  const history = useQuery({ queryKey: ["day-closing-history", skip], queryFn: () => api.get<Closing[]>(`/day-closing?skip=${skip}&limit=30`) });
  const difference = Number(actual) - Number(preview.data?.expected_cash ?? 0);
  async function submit() {
    if (!actual || Number(actual) < 0 || !preview.data) return;
    setBusy(true); setError(""); setSaved("");
    try { await api.post<Closing>("/day-closing", { business_date: day, opening_cash: opening, actual_cash: actual, notes: notes || null }); setSaved("Day closing saved. A manager can now approve it."); await client.invalidateQueries({ queryKey: ["day-closing-history"] }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save day closing. Your entries are still here."); }
    finally { setBusy(false); }
  }
  async function approve(id: string) {
    setBusy(true); setError("");
    try { await api.post(`/day-closing/${id}/approve`, {}); setSaved("Day closing approved and kept in history."); await client.invalidateQueries({ queryKey: ["day-closing-history"] }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not approve day closing."); }
    finally { setBusy(false); }
  }
  return <div className="space-y-6"><PageHeader title="Day Closing" subtitle="Count the shop cash, check the difference, and save the daily report." />
    {error && <ErrorState message={error} />}{saved && <p role="status" className="rounded-lg bg-emerald-50 p-4 font-semibold text-emerald-900">{saved}</p>}
    {canSubmit && <section className="grid gap-5 lg:grid-cols-2">
      <div className="ds-surface space-y-5 p-5"><h2 className="text-xl font-bold">1. Count your cash</h2><label className="field-label">Closing date<input className="field-input" type="date" required value={day} max={today()} onChange={(e) => setDay(e.target.value)} /></label><label className="field-label">Opening cash<input className="field-input" type="number" min="0" step="0.01" value={opening} onChange={(e) => setOpening(e.target.value)} /></label><label className="field-label">Actual cash in the drawer<input className="field-input text-xl" type="number" min="0" step="0.01" required value={actual} onChange={(e) => setActual(e.target.value)} /></label><label className="field-label">Notes (optional)<textarea className="field-input" maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} /></label></div>
      <div className="ds-surface space-y-5 p-5"><h2 className="text-xl font-bold">2. Check and save</h2>{preview.error ? <ErrorState message={preview.error.message} /> : preview.data ? <><dl className="divide-y divide-border">{([["Opening cash", preview.data.opening_cash], ["+ Cash sales", preview.data.cash_sales], ["− Cash refunds", preview.data.cash_refunds], ["− Cash expenses", preview.data.cash_expenses], ["+ Customer cash payments", preview.data.customer_cash_payments], ["− Supplier cash payments", preview.data.supplier_cash_payments ?? "0"], ["Expected closing cash", preview.data.expected_cash]]).map(([label, amount]) => <div key={label} className="flex justify-between gap-3 py-3"><dt>{label}</dt><dd className="font-semibold">{money(amount)}</dd></div>)}</dl><p className="text-sm">Business day: {preview.data.timezone}. {preview.data.bills} bills.</p>{actual !== "" && <p role="status" className="rounded-lg bg-slate-100 p-4 text-lg font-bold">{difference === 0 ? "Cash matches" : difference < 0 ? `Shortage: ${money(-difference)}` : `Excess: ${money(difference)}`}</p>}<Button className="w-full" disabled={busy || !actual || Number(actual) < 0 || preview.isFetching} onClick={() => void submit()}><Save size={19} />{busy ? "Saving…" : "Save Day Closing"}</Button><p className="text-sm">This report covers the whole shop for the selected date. Save after the day's transactions are finished.</p></> : <p role="status">Calculating cash…</p>}</div>
      {preview.data && <div className="flex flex-wrap gap-3 lg:col-span-2">{Object.entries(preview.data.payment_totals).map(([mode, amount]) => <div key={mode} className="ds-surface min-w-32 flex-1 p-4"><p className="font-medium">{mode}</p><p className="mt-2 text-xl font-bold">{money(amount)}</p></div>)}</div>}
    </section>}
    <section className="ds-surface p-5"><h2 className="mb-4 text-xl font-bold">Closing history</h2>{history.error ? <ErrorState message={history.error.message} /> : history.isLoading ? <p>Loading history…</p> : !history.data?.length ? <p>No day closing has been saved yet.</p> : <div className="divide-y divide-border">{history.data.map((entry) => <article key={entry.id} className="grid gap-4 py-5 sm:grid-cols-[1fr_auto]"><div><div className="flex flex-wrap items-center gap-3"><h3 className="text-lg font-bold">{entry.business_date}</h3><span className="rounded-lg bg-slate-100 px-3 py-2 font-semibold">{entry.status === "APPROVED" ? "Approved" : "Awaiting approval"}</span></div><p className="mt-2">Actual {money(entry.actual_cash)} · Expected {money(entry.expected_cash)} · {Number(entry.difference) === 0 ? "Cash matches" : Number(entry.difference) < 0 ? `Shortage ${money(-Number(entry.difference))}` : `Excess ${money(entry.difference)}`}</p>{entry.notes && <p className="mt-2">{entry.notes}</p>}<details className="mt-2"><summary className="cursor-pointer py-2">Payment summary</summary>{Object.entries(entry.summary_json.payment_totals).map(([mode, amount]) => <p key={mode}>{mode}: {money(amount)}</p>)}</details></div><div className="flex flex-wrap gap-3 self-start">{entry.status === "SUBMITTED" && canSubmit && <Button variant="secondary" onClick={() => { setDay(entry.business_date); setOpening(entry.opening_cash); setActual(entry.actual_cash); setNotes(entry.notes ?? ""); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Review / update</Button>}{entry.status === "SUBMITTED" && canApprove && <Button disabled={busy} onClick={() => void approve(entry.id)}><CheckCheck size={19} />Approve Closing</Button>}</div></article>)}</div>}<div className="mt-4 flex justify-end gap-3"><Button variant="secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - 30))}>Newer</Button><Button variant="secondary" disabled={(history.data?.length ?? 0) < 30} onClick={() => setSkip(skip + 30)}>Older</Button></div></section>
  </div>;
}

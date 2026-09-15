import LowStockReport from "../components/LowStockReport";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, BarChart3, CalendarDays, IndianRupee, PackageSearch, ReceiptText, RefreshCw, TrendingUp } from "lucide-react";
import { ApiError, api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { Button } from "../components/ui/button";
import type { ReportsSummary } from "../types";
import { money } from "../utils/format";

type DateRange = { startDate: string; endDate: string };

function localDate(offsetDays = 0): string {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function reportError(error: unknown): { message: string; requestId?: string; isServerError: boolean; isUnauthorized: boolean } {
  if (error instanceof ApiError) {
    if (error.status === 0) return { message: "Unable to connect to the server. Check your connection and try again.", isServerError: false, isUnauthorized: false };
    if (error.status === 401) return { message: "Your session has expired. Redirecting to sign in…", isServerError: false, isUnauthorized: true };
    if (error.code === "invalid_date_range") return { message: "End date cannot be earlier than Start date.", isServerError: false, isUnauthorized: false };
    if (error.code === "report_calculation_failed" || error.status >= 500) return { message: "Unable to generate this report right now.", requestId: error.requestId, isServerError: true, isUnauthorized: false };
    return { message: error.message, isServerError: false, isUnauthorized: false };
  }
  return { message: "Unable to generate this report right now.", isServerError: true, isUnauthorized: false };
}

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(() => localDate(-30));
  const [endDate, setEndDate] = useState(() => localDate());
  const [appliedRange, setAppliedRange] = useState<DateRange>(() => ({ startDate: localDate(-30), endDate: localDate() }));
  const [exporting, setExporting] = useState(false);
  const [dateError, setDateError] = useState("");
  const reportsQuery = useQuery({
    queryKey: ["reports", appliedRange.startDate, appliedRange.endDate],
    queryFn: () => api.get<ReportsSummary>(`/reports/summary?start_date=${appliedRange.startDate}&end_date=${appliedRange.endDate}`),
  });
  const error = reportsQuery.error ? reportError(reportsQuery.error) : undefined;

  function applyRange() {
    if (!startDate || !endDate || endDate < startDate) {
      setDateError("End date cannot be earlier than Start date.");
      return;
    }
    setDateError("");
    setAppliedRange({ startDate, endDate });
  }

  async function exportReports() { setExporting(true); setDateError(""); try { const blob = await api.getBlob(`/reports/export.xlsx?start_date=${appliedRange.startDate}&end_date=${appliedRange.endDate}`); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "rainbow-business-reports.xlsx"; link.click(); URL.revokeObjectURL(url); } catch (cause) { setDateError(cause instanceof Error ? cause.message : "Could not download reports."); } finally { setExporting(false); } }
  function preset(days: number, yesterday = false, month = false) { const end = localDate(yesterday ? -1 : 0); const start = month ? `${end.slice(0, 7)}-01` : localDate(yesterday ? -1 : -days); setStartDate(start); setEndDate(end); setAppliedRange({ startDate: start, endDate: end }); setDateError(""); }
  return (
    <div className="space-y-6">
      <PageHeader title="Reports" subtitle="Review profit, cash flow, and inventory value from live transactions" />
      <div className="flex flex-wrap gap-2">{[["Today",0],["Yesterday",-1],["7 days",6],["30 days",29],["This month",-2]].map(([label,days]) => <Button key={label} type="button" variant="secondary" onClick={() => preset(Number(days), days === -1, days === -2)}>{label}</Button>)}</div><form className="flex flex-wrap items-end gap-3 rounded-md border border-line bg-white p-4" onSubmit={(event) => { event.preventDefault(); applyRange(); }}>
        <label className="grid gap-1 text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><CalendarDays size={15} /> Start</span><input aria-label="Start date" className="form-input" type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setDateError(""); }} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><CalendarDays size={15} /> End</span><input aria-label="End date" className="form-input" type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setDateError(""); }} /></label>
        <Button type="submit" disabled={reportsQuery.isFetching}><RefreshCw size={16} className={reportsQuery.isFetching ? "animate-spin" : ""} /> Apply</Button>
        <Button type="button" variant="secondary" disabled={exporting || reportsQuery.isFetching} onClick={() => void exportReports()}>{exporting ? "Preparing Excel…" : "Download all reports (Excel)"}</Button>{dateError ? <div className="basis-full text-sm text-error" role="alert">{dateError}</div> : null}
      </form>

      <p className="text-sm text-muted">Excel includes sales, returns, recorded GST, purchases, supplier credits, stock movements, inventory, low stock, expenses, payment modes, closing and account balances. Inventory and balances are current snapshots.</p><LowStockReport />
      {reportsQuery.isFetching ? <div className="flex items-center gap-2 text-sm text-muted" aria-live="polite"><RefreshCw size={16} className="animate-spin" /> Generating your report…</div> : null}
      {reportsQuery.isLoading ? <SkeletonRows rows={6} /> : error ? (
        <section className="flex flex-wrap items-center gap-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-error" role="alert">
          <div className="flex min-w-0 items-center gap-2"><AlertCircle size={17} className="shrink-0" /><div><span>{error.message}</span>{error.isServerError && error.requestId ? <span className="ml-2 text-xs text-red-700">Reference ID: {error.requestId}</span> : null}</div></div>
          {!error.isUnauthorized ? <Button type="button" size="sm" variant="secondary" onClick={() => void reportsQuery.refetch()} disabled={reportsQuery.isFetching}><RefreshCw size={16} /> Retry</Button> : null}
        </section>
      ) : reportsQuery.data && !reportsQuery.data.has_report_data ? (
        <EmptyState icon={ReceiptText} title="No transactions found for this period." description="Try a different date range, or record a sale, purchase, expense, or payment to generate a report." />
      ) : reportsQuery.data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric icon={IndianRupee} label="Sales" value={money(reportsQuery.data.profit_and_loss.sales_total)} />
            <Metric icon={TrendingUp} label="Gross profit" value={money(reportsQuery.data.profit_and_loss.gross_profit)} tone="good" />
            <Metric icon={BarChart3} label="Net profit" value={money(reportsQuery.data.profit_and_loss.net_profit)} tone={Number(reportsQuery.data.profit_and_loss.net_profit) >= 0 ? "good" : "warn"} />
            <Metric icon={PackageSearch} label="Inventory value" value={money(reportsQuery.data.inventory_valuation.purchase_value)} />
          </div>
          <section className="grid gap-5 xl:grid-cols-3">
            <ReportPanel title="Profit and loss" rows={[["Sales", reportsQuery.data.profit_and_loss.sales_total], ["Purchase value", reportsQuery.data.profit_and_loss.purchase_total], ["Expenses", reportsQuery.data.profit_and_loss.expense_total], ["Gross profit", reportsQuery.data.profit_and_loss.gross_profit], ["Net profit", reportsQuery.data.profit_and_loss.net_profit]]} />
            <ReportPanel title="Cash flow" rows={[["Cash sales", reportsQuery.data.cash_flow.cash_sales], ["Customer collections", reportsQuery.data.cash_flow.customer_payments], ["Supplier payments", reportsQuery.data.cash_flow.supplier_payments], ["Expenses", reportsQuery.data.cash_flow.expenses], ["Net cash flow", reportsQuery.data.cash_flow.net_cash_flow]]} />
            <ReportPanel title="Inventory valuation" rows={[["Pieces in stock", reportsQuery.data.inventory_valuation.total_stock], ["Purchase value", reportsQuery.data.inventory_valuation.purchase_value], ["Selling value", reportsQuery.data.inventory_valuation.selling_value], ["Potential margin", reportsQuery.data.inventory_valuation.potential_margin]]} />
          </section>
        </>
      ) : null}
    </div>
  );
}

function Metric({ icon: Icon, label, value, tone }: { icon: typeof IndianRupee; label: string; value: string; tone?: "good" | "warn" }) {
  const toneClass = tone === "good" ? "text-emerald-700" : tone === "warn" ? "text-rose-700" : "text-slate-950";
  return <div className="rounded-md border border-line bg-white p-4"><div className="flex items-center gap-2 text-sm text-slate-500"><Icon size={16} /> {label}</div><div className={`mt-2 text-2xl font-bold ${toneClass}`}>{value}</div></div>;
}

function ReportPanel({ title, rows }: { title: string; rows: Array<[string, string | number]> }) {
  return <div className="rounded-md border border-line bg-white p-4"><h2 className="font-semibold text-slate-950">{title}</h2><div className="mt-4 divide-y divide-line">{rows.map(([label, value]) => <div key={label} className="flex items-center justify-between gap-4 py-2 text-sm"><span className="text-slate-500">{label}</span><span className="font-semibold text-slate-950">{typeof value === "number" ? value : money(value)}</span></div>)}</div></div>;
}

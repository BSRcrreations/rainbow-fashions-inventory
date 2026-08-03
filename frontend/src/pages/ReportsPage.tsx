import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, CalendarDays, IndianRupee, PackageSearch, TrendingUp } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import type { ReportsSummary } from "../types";
import { money } from "../utils/format";

const today = new Date().toISOString().slice(0, 10);
const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(start);
  const [endDate, setEndDate] = useState(today);
  const reportsQuery = useQuery({ queryKey: ["reports", startDate, endDate], queryFn: () => api.get<ReportsSummary>(`/reports/summary?start_date=${startDate}&end_date=${endDate}`) });

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" subtitle="Review profit, cash flow, and inventory value from live transactions" />
      <div className="flex flex-wrap gap-3 rounded-md border border-line bg-white p-4">
        <label className="grid gap-1 text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><CalendarDays size={15} /> Start</span><input className="form-input" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><CalendarDays size={15} /> End</span><input className="form-input" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
      </div>
      {reportsQuery.isLoading ? <SkeletonRows rows={6} /> : reportsQuery.error ? <ErrorState message={reportsQuery.error instanceof Error ? reportsQuery.error.message : "Unable to load reports"} /> : reportsQuery.data ? (
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

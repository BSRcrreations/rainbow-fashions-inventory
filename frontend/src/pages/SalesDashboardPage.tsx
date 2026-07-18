import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Banknote, Boxes, CalendarDays, IndianRupee, Package, ReceiptText, ShoppingBag, Smartphone, TrendingUp, WalletCards } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import { Button } from "../components/ui/button";
import type { SalesDashboard } from "../types";
import { money, shortDate } from "../utils/format";

type Preset = "today" | "yesterday" | "week" | "month" | "custom";

const periodNames: Record<Preset, string> = {
  today: "Today's",
  yesterday: "Yesterday's",
  week: "This Week's",
  month: "This Month's",
  custom: "Selected Period",
};

function CollectionRow({ icon: Icon, label, value, tone }: { icon: typeof Banknote; label: string; value: string; tone: "cash" | "upi" | "total" }) {
  const tones = {
    cash: "bg-emerald-50 text-emerald-700",
    upi: "bg-sky-50 text-sky-700",
    total: "bg-gradient-to-br from-teal-50 to-emerald-100 text-teal-800",
  };
  return (
    <div className={`flex items-center justify-between gap-4 px-5 py-4 sm:px-6 ${tone === "total" ? "border-t-2 border-teal-100" : "border-b border-slate-100"}`}>
      <div className="flex min-w-0 items-center gap-3"><span className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${tones[tone]}`}><Icon size={21} /></span><span className={`${tone === "total" ? "font-bold text-slate-950" : "font-medium text-slate-600"}`}>{label}</span></div>
      <strong className={`${tone === "total" ? "text-2xl text-teal-800" : "text-lg text-slate-950"}`}>{money(value)}</strong>
    </div>
  );
}

export default function SalesDashboardPage() {
  const [preset, setPreset] = useState<Preset>("today");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const params = new URLSearchParams({ preset });
  if (preset === "custom" && startDate && endDate) { params.set("start_date", startDate); params.set("end_date", endDate); }
  const enabled = preset !== "custom" || Boolean(startDate && endDate);
  const query = useQuery({ queryKey: ["sales-dashboard", preset, startDate, endDate], queryFn: () => api.get<SalesDashboard>(`/sales/dashboard?${params}`), enabled });
  const data = query.data;
  const periodName = periodNames[preset];

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Your retail performance and inventory snapshot" />
      <div className="mb-6 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="grid grid-cols-5 gap-1 sm:flex" aria-label="Dashboard period">
          {([['today','Today'],['yesterday','Yesterday'],['week','This Week'],['month','This Month'],['custom','Custom']] as Array<[Preset,string]>).map(([value, label]) => <Button key={value} type="button" size="sm" variant={preset === value ? "default" : "ghost"} className="w-full whitespace-nowrap px-1 text-[10px] sm:w-auto sm:px-4 sm:text-sm" onClick={() => setPreset(value)}>{label}</Button>)}
        </div>
        {preset === "custom" ? <div className="flex flex-wrap items-center gap-2"><CalendarDays size={17} className="text-slate-500" /><input aria-label="Start date" className="field-input w-auto" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /><span className="text-sm text-slate-400">to</span><input aria-label="End date" className="field-input w-auto" type="date" min={startDate} value={endDate} onChange={(event) => setEndDate(event.target.value)} /></div> : null}
      </div>

      {!enabled ? <EmptyState icon={CalendarDays} title="Choose a date range" description="Select both start and end dates to load dashboard values." /> : query.isLoading ? <SkeletonRows rows={7} /> : query.error || !data ? <ErrorState message={query.error instanceof Error ? query.error.message : "Unable to load dashboard"} /> : (
        <div className="space-y-6">
          <section aria-label="Selected period performance" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 xl:gap-6">
            <StatCard label={`${periodName} Revenue`} value={money(data.selected.sales)} tone="teal" icon={IndianRupee} />
            <StatCard label={`${periodName} Orders`} value={`${data.selected.orders} Orders`} tone="slate" icon={ReceiptText} />
            <StatCard label={`${periodName} Profit`} value={money(data.selected.profit)} tone="amber" icon={TrendingUp} />
          </section>

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_4px_18px_rgba(15,23,42,0.05)]">
            <div className="border-b border-slate-100 px-5 py-4 sm:px-6"><h2 className="text-lg font-semibold text-slate-950">{periodName} Collection</h2><p className="mt-1 text-sm text-slate-500">Collected across completed invoices for this period</p></div>
            <CollectionRow icon={Banknote} label="Cash Collection" value={data.collection?.cash ?? "0"} tone="cash" />
            <CollectionRow icon={Smartphone} label="UPI Collection" value={data.collection?.upi ?? "0"} tone="upi" />
            <CollectionRow icon={WalletCards} label="Total Collection" value={data.collection?.total ?? data.selected.sales} tone="total" />
            {Number(data.collection?.card) || Number(data.collection?.other) ? <div className="bg-slate-50 px-6 py-2 text-right text-xs text-slate-500">Includes {money(Number(data.collection?.card ?? 0) + Number(data.collection?.other ?? 0))} from card and other methods</div> : null}
          </section>

          <section aria-label="Sales and inventory value" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 xl:gap-6">
            <StatCard label="Weekly Sales" value={money(data.week.sales)} tone="teal" icon={ShoppingBag} />
            <StatCard label="Monthly Sales" value={money(data.month.sales)} tone="amber" icon={WalletCards} />
            <StatCard label="Inventory Value" value={money(data.inventory_value ?? 0)} tone="slate" icon={IndianRupee} />
          </section>

          <section aria-label="Inventory totals" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 xl:gap-6">
            <StatCard label="Total Stock Quantity" value={`${(data.total_stock ?? 0).toLocaleString("en-IN")} Units`} tone="teal" icon={Boxes} />
            <StatCard label="Total Products" value={`${(data.total_products ?? 0).toLocaleString("en-IN")} Products`} tone="slate" icon={Package} />
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <section className="overflow-hidden rounded-lg border border-slate-200 bg-white"><h2 className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-lg font-semibold"><AlertTriangle size={19} className="text-amber-600" /> Low Stock Alerts</h2><div className="divide-y divide-slate-100">{data.low_stock.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 px-5 py-4 text-sm transition hover:bg-amber-50/50"><div className="min-w-0"><div className="truncate font-semibold text-slate-900">{item.name}</div><div className="mt-0.5 text-xs text-slate-500">Minimum level: {item.minimum_stock}</div></div><span className="rounded-full bg-amber-100 px-3 py-1 font-bold text-amber-800">{item.current_stock} left</span></div>)}{!data.low_stock.length ? <EmptyState icon={Package} title="Stock levels look good" description="Products below their minimum level will appear here." /> : null}</div></section>
            <section className="overflow-hidden rounded-lg border border-slate-200 bg-white"><h2 className="border-b border-slate-100 px-5 py-4 text-lg font-semibold">Recent Sales</h2><div className="divide-y divide-slate-100">{data.recent_sales.map((sale) => <div key={sale.id} className="flex items-center justify-between gap-4 px-5 py-4 text-sm transition hover:bg-teal-50/50"><div className="min-w-0"><div className="truncate font-semibold text-slate-900">{sale.invoice_number}</div><div className="mt-0.5 truncate text-xs text-slate-500">{sale.customer_name || "Walk-in"} · {sale.payment_mode} · {shortDate(sale.sale_date)}</div></div><strong className="shrink-0 text-teal-800">{money(sale.total_amount)}</strong></div>)}{!data.recent_sales.length ? <EmptyState icon={ReceiptText} title="No recent sales" description="Completed invoices for this period will appear here." /> : null}</div></section>
          </div>
        </div>
      )}
    </>
  );
}

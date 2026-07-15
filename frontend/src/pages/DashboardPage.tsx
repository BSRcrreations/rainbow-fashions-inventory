import { useEffect, useState } from "react";
import { AlertTriangle, Boxes, IndianRupee, Package } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import type { DashboardSummary } from "../types";
import { money, shortDate } from "../utils/format";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<DashboardSummary>("/dashboard/summary").then(setSummary).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="rounded-md bg-rose-50 p-4 text-rose-700">{error}</div>;
  if (!summary) return <div className="text-sm text-slate-500">Loading dashboard</div>;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live inventory snapshot" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Products" value={summary.total_products} tone="teal" icon={Package} />
        <StatCard label="Total Stock" value={summary.total_stock} tone="slate" icon={Boxes} />
        <StatCard label="Low Stock" value={summary.low_stock_count} tone="rose" icon={AlertTriangle} />
        <StatCard label="Inventory Value" value={money(summary.inventory_value)} tone="amber" icon={IndianRupee} />
      </div>
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 font-semibold">Low stock</div>
          <div className="divide-y divide-line">
            {summary.low_stock_products.map((product) => (
              <div key={product.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div>
                  <div className="font-medium text-slate-900">{product.name}</div>
                  <div className="text-slate-500">{product.brand_name} / {product.category_name} / {product.size} / {product.color}</div>
                </div>
                <div className="text-right font-semibold text-rose-700">{product.current_stock} / {product.minimum_stock}</div>
              </div>
            ))}
            {!summary.low_stock_products.length ? <div className="px-4 py-6 text-sm text-slate-500">No low stock items</div> : null}
          </div>
        </section>
        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 font-semibold">Recent stock changes</div>
          <div className="divide-y divide-line">
            {summary.recent_stock_changes.map((movement) => (
              <div key={movement.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div>
                  <StatusBadge value={movement.movement_type} />
                  <div className="mt-1 text-slate-500">{shortDate(movement.movement_date)}</div>
                </div>
                <div className="text-right text-slate-700">
                  {movement.before_stock} to {movement.after_stock}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

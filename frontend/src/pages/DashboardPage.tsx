import { useEffect, useState } from "react";
import { AlertTriangle, Boxes, IndianRupee, Package, Receipt, Shuffle } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { DashboardSummary } from "../types";
import { money, shortDate } from "../utils/format";

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<DashboardSummary>("/dashboard/summary")
      .then(setSummary)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (error) return <ErrorState message={error} />;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live inventory snapshot" />
      {loading || !summary ? (
        <SkeletonRows rows={6} />
      ) : (
        <>
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
                  <div key={product.id} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-900">{product.name}</div>
                      <div className="truncate text-slate-500">{product.brand_name} / {product.category_name} / {product.size} / {product.color}</div>
                    </div>
                    <div className="font-semibold text-rose-700 sm:text-right">{product.current_stock} / {product.minimum_stock}</div>
                  </div>
                ))}
                {!summary.low_stock_products.length ? (
                  <EmptyState icon={Package} title="No low stock items" description="Products above their minimum stock level will stay out of this list." />
                ) : null}
              </div>
            </section>
            <section className="rounded-md border border-line bg-white">
              <div className="border-b border-line px-4 py-3 font-semibold">Recent stock changes</div>
              <div className="divide-y divide-line">
                {summary.recent_stock_changes.map((movement) => (
                  <div key={movement.id} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <div>
                      <StatusBadge value={movement.movement_type} />
                      <div className="mt-1 text-slate-500">{shortDate(movement.movement_date)}</div>
                    </div>
                    <div className="text-slate-700 sm:text-right">
                      {movement.before_stock} to {movement.after_stock}
                    </div>
                  </div>
                ))}
                {!summary.recent_stock_changes.length ? (
                  <EmptyState icon={Shuffle} title="No stock movements" description="Purchases and manual adjustments will appear here once stock changes." />
                ) : null}
              </div>
            </section>
          </div>
          {user?.role === "OWNER" && summary.today_sales ? (
            <section className="mt-6 rounded-md border border-line bg-white">
              <div className="border-b border-line px-4 py-3 font-semibold">Today's sales</div>
              <div className="grid gap-4 px-4 py-3 sm:grid-cols-2">
                <div className="rounded-md bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Transactions</div>
                  <div className="text-xl font-bold text-slate-900">{summary.today_sales.total_count}</div>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Items sold</div>
                  <div className="text-xl font-bold text-slate-900">{summary.today_sales.total_qty}</div>
                </div>
              </div>
              <div className="divide-y divide-line">
                {summary.today_sales.sales.map((sale) => (
                  <div key={sale.id} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-900">{sale.product_name} / {sale.size} / {sale.color}</div>
                      <div className="truncate text-slate-500">{shortDate(sale.movement_date)} {sale.reference ? `· ${sale.reference}` : ""}</div>
                    </div>
                    <div className="font-semibold text-slate-700 sm:text-right">-{sale.qty} pcs</div>
                  </div>
                ))}
                {!summary.today_sales.sales.length ? (
                  <EmptyState icon={Receipt} title="No sales today" description="Sales recorded on the Sales page will appear here." />
                ) : null}
              </div>
            </section>
          ) : null}
        </>
      )}
    </>
  );
}

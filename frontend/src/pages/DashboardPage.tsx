import { useEffect, useState } from "react";
import { AlertTriangle, Boxes, IndianRupee, Package, Shuffle } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import type { DashboardSummary } from "../types";
import { money, shortDate } from "../utils/format";

function DistributionBars({ title, items }: { title: string; items: Array<{ label: string; value: number }> }) {
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <section className="rounded-md border border-line bg-white">
      <div className="border-b border-line px-4 py-3 font-semibold">{title}</div>
      <div className="space-y-3 p-4">
        {items.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex justify-between gap-3 text-sm">
              <span className="truncate text-slate-700">{item.label}</span>
              <span className="font-medium text-slate-900">{item.value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded bg-slate-100">
              <div className="h-full rounded bg-teal-600" style={{ width: `${Math.max((item.value / max) * 100, item.value ? 6 : 0)}%` }} />
            </div>
          </div>
        ))}
        {!items.length ? <div className="text-sm text-slate-500">No data yet</div> : null}
      </div>
    </section>
  );
}

export default function DashboardPage() {
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
              <div className="border-b border-line px-4 py-3 font-semibold">Latest products</div>
              <div className="divide-y divide-line">
                {summary.latest_products.map((product) => (
                  <div key={product.id} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-900">{product.name}</div>
                      <div className="truncate text-slate-500">{product.sku || product.barcode || "No SKU"} / {product.brand?.name} / {product.category?.name}</div>
                    </div>
                    <div className="font-medium text-slate-700 sm:text-right">{money(product.selling_price)}</div>
                  </div>
                ))}
                {!summary.latest_products.length ? <EmptyState icon={Package} title="No latest products" description="Newly added products will appear here." /> : null}
              </div>
            </section>
            <section className="rounded-md border border-line bg-white">
              <div className="border-b border-line px-4 py-3 font-semibold">Top selling products</div>
              <EmptyState icon={Package} title="Sales data pending" description="Top selling products will appear once the sales module is available." />
            </section>
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
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <DistributionBars title="Stock distribution" items={summary.stock_distribution} />
            <DistributionBars title="Category distribution" items={summary.category_distribution} />
            <DistributionBars title="Brand distribution" items={summary.brand_distribution} />
          </div>
        </>
      )}
    </>
  );
}

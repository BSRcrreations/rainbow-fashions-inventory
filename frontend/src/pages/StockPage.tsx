import { FormEvent, useEffect, useMemo, useState } from "react";
import { Download, History, SlidersHorizontal } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Product, StockHistory, StockMovementType } from "../types";
import { shortDate } from "../utils/format";

export default function StockPage() {
  const toast = useToast();
  const [history, setHistory] = useState<StockHistory[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [filterProductId, setFilterProductId] = useState("");
  const [movementFilter, setMovementFilter] = useState("");
  const [direction, setDirection] = useState("INCREASE");
  const [qty, setQty] = useState("1");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const filtered = useMemo(() => Boolean(filterProductId || movementFilter), [filterProductId, movementFilter]);

  function historyQuery() {
    const params = new URLSearchParams();
    if (filterProductId) params.set("product_id", filterProductId);
    if (movementFilter) params.set("movement_type", movementFilter);
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  async function load() {
    setError("");
    try {
      const [historyData, productData] = await Promise.all([
        api.get<StockHistory[]>(`/stock/history${historyQuery()}`),
        api.get<Product[]>("/products"),
      ]);
      setHistory(historyData);
      setProducts(productData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load stock history");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function validateAdjustment() {
    if (!productId) return "Product is required";
    const amount = Number(qty);
    if (!Number.isInteger(amount) || amount <= 0) return "Adjustment quantity must be a positive whole number";
    const product = products.find((item) => item.id === productId);
    if (product && direction === "DECREASE" && product.current_stock - amount < 0) return "Stock cannot become negative";
    return "";
  }

  async function adjust(event: FormEvent) {
    event.preventDefault();
    const validationError = validateAdjustment();
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError("");
    try {
      await api.post<StockHistory>("/stock/adjustments", { product_id: productId, direction, qty: Number(qty), reference: reference.trim() || null });
      setReference("");
      toast.success("Stock adjusted");
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Stock adjustment failed";
      setError(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  async function exportCsv() {
    setExporting(true);
    setError("");
    try {
      const blob = await api.getBlob(`/stock/history/export${historyQuery()}`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "stock-history.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Stock history exported");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to export stock history";
      setError(message);
      toast.error(message);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Stock"
        subtitle="Adjustments and movement history"
        actions={
          <Button type="button" variant="secondary" onClick={() => void exportCsv()} disabled={exporting}>
            <Download size={16} /> {exporting ? "Exporting" : "Export CSV"}
          </Button>
        }
      />
      <form onSubmit={adjust} className="mb-5 grid gap-3 rounded-md border border-line bg-white p-4 md:grid-cols-5">
        <select className="focus-ring h-10 rounded-md border border-line px-3 md:col-span-2" value={productId} onChange={(event) => setProductId(event.target.value)} disabled={pending}>
          <option value="">Product</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name} / {product.size} / {product.color}</option>)}
        </select>
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={direction} onChange={(event) => setDirection(event.target.value)} disabled={pending}>
          <option value="INCREASE">Increase</option>
          <option value="DECREASE">Decrease</option>
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" type="number" min="1" value={qty} onChange={(event) => setQty(event.target.value)} disabled={pending} />
        <Button type="submit" disabled={pending}>
          <SlidersHorizontal size={16} /> {pending ? "Adjusting" : "Adjust"}
        </Button>
        <input className="focus-ring h-10 rounded-md border border-line px-3 md:col-span-5" placeholder="Reference" value={reference} onChange={(event) => setReference(event.target.value)} disabled={pending} />
      </form>
      <div className="mb-4 grid gap-2 sm:grid-cols-[minmax(0,1fr)_220px_auto]">
        <select className="focus-ring h-10 rounded-md border border-line bg-white px-3" value={filterProductId} onChange={(event) => setFilterProductId(event.target.value)}>
          <option value="">All products</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name} / {product.size} / {product.color}</option>)}
        </select>
        <select className="focus-ring h-10 rounded-md border border-line bg-white px-3" value={movementFilter} onChange={(event) => setMovementFilter(event.target.value)}>
          <option value="">All movement types</option>
          {(["PURCHASE", "SALE", "ADJUSTMENT"] satisfies StockMovementType[]).map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
        <Button type="button" variant="secondary" onClick={() => void load()}>Apply filters</Button>
      </div>
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {loading ? (
        <SkeletonRows rows={6} />
      ) : history.length ? (
        <div className="overflow-x-auto rounded-md border border-line bg-white">
          <table className="min-w-[760px] divide-y divide-line text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Qty</th>
                <th className="px-4 py-3">Before</th>
                <th className="px-4 py-3">After</th>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {history.map((movement) => (
                <tr key={movement.id}>
                  <td className="px-4 py-3"><StatusBadge value={movement.movement_type} /></td>
                  <td className="px-4 py-3">{movement.qty}</td>
                  <td className="px-4 py-3">{movement.before_stock}</td>
                  <td className="px-4 py-3">{movement.after_stock}</td>
                  <td className="px-4 py-3">{movement.reference ?? "-"}</td>
                  <td className="px-4 py-3">{shortDate(movement.movement_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-md border border-line bg-white">
          <EmptyState
            icon={History}
            title={filtered ? "No matching stock movements" : "No stock movements yet"}
            description={filtered ? "Try a different product or movement type." : "Manual adjustments and confirmed purchases will appear here."}
          />
        </div>
      )}
    </>
  );
}

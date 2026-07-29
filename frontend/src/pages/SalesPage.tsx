import { FormEvent, useCallback, useEffect, useState } from "react";
import { Receipt, ShoppingCart } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Product, StockHistory } from "../types";
import { shortDate } from "../utils/format";

export default function SalesPage() {
  const toast = useToast();
  const [products, setProducts] = useState<Product[]>([]);
  const [sales, setSales] = useState<StockHistory[]>([]);
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("1");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  function todayRangeQuery() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    const params = new URLSearchParams();
    params.set("movement_type", "SALE");
    params.set("from_date", start.toISOString());
    params.set("to_date", end.toISOString());
    return `?${params.toString()}`;
  }

  const load = useCallback(async () => {
    setError("");
    try {
      const [productData, salesData] = await Promise.all([
        api.get<Product[]>("/products"),
        api.get<StockHistory[]>(`/stock/history${todayRangeQuery()}`),
      ]);
      setProducts(productData);
      setSales(salesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load sales");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function productName(id: string) {
    return products.find((p) => p.id === id)?.name ?? id.slice(0, 8);
  }

  function validate() {
    if (!productId) return "Product is required";
    const amount = Number(qty);
    if (!Number.isInteger(amount) || amount <= 0) return "Quantity must be a positive whole number";
    return "";
  }

  async function recordSale(event: FormEvent) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError("");
    try {
      await api.post<StockHistory>("/stock/sales", { product_id: productId, qty: Number(qty), reference: reference.trim() || null });
      setProductId("");
      setQty("1");
      setReference("");
      toast.success("Sale recorded");
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to record sale";
      setError(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <PageHeader title="Sales" subtitle="Record sales and track today's activity" />
      <form onSubmit={recordSale} className="mb-5 grid gap-3 rounded-md border border-line bg-white p-4 md:grid-cols-5">
        <select className="focus-ring h-10 rounded-md border border-line px-3 md:col-span-2" value={productId} onChange={(event) => setProductId(event.target.value)} disabled={pending}>
          <option value="">Product</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name} / {product.size} / {product.color}</option>)}
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" type="number" min="1" value={qty} onChange={(event) => setQty(event.target.value)} disabled={pending} placeholder="Qty" />
        <input className="focus-ring h-10 rounded-md border border-line px-3" value={reference} onChange={(event) => setReference(event.target.value)} disabled={pending} placeholder="Reference / customer" />
        <Button type="submit" disabled={pending}>
          <ShoppingCart size={16} /> {pending ? "Saving" : "Record sale"}
        </Button>
      </form>

      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}

      {loading ? (
        <SkeletonRows rows={6} />
      ) : sales.length ? (
        <div className="overflow-x-auto rounded-md border border-line bg-white">
          <table className="min-w-[760px] divide-y divide-line text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Qty</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {sales.map((sale) => (
                <tr key={sale.id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{productName(sale.product_id)}</td>
                  <td className="px-4 py-3"><StatusBadge value={sale.movement_type} /></td>
                  <td className="px-4 py-3">{sale.qty}</td>
                  <td className="px-4 py-3">{sale.before_stock} to {sale.after_stock}</td>
                  <td className="px-4 py-3">{sale.reference ?? "-"}</td>
                  <td className="px-4 py-3">{shortDate(sale.movement_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-md border border-line bg-white">
          <EmptyState icon={Receipt} title="No sales today" description="Use the form above to record a sale." />
        </div>
      )}
    </>
  );
}

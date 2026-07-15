import { FormEvent, useEffect, useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import type { Product, StockHistory } from "../types";
import { shortDate } from "../utils/format";

export default function StockPage() {
  const [history, setHistory] = useState<StockHistory[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [direction, setDirection] = useState("INCREASE");
  const [qty, setQty] = useState("1");
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [historyData, productData] = await Promise.all([
      api.get<StockHistory[]>("/stock/history"),
      api.get<Product[]>("/products")
    ]);
    setHistory(historyData);
    setProducts(productData);
  }

  useEffect(() => {
    void load();
  }, []);

  async function adjust(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post<StockHistory>("/stock/adjustments", { product_id: productId, direction, qty: Number(qty), reference: reference || null });
      setReference("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stock adjustment failed");
    }
  }

  return (
    <>
      <PageHeader title="Stock" subtitle="Adjustments and movement history" />
      <form onSubmit={adjust} className="mb-5 grid gap-3 rounded-md border border-line bg-white p-4 md:grid-cols-5">
        <select className="focus-ring h-10 rounded-md border border-line px-3 md:col-span-2" value={productId} onChange={(event) => setProductId(event.target.value)} required>
          <option value="">Product</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name} / {product.size} / {product.color}</option>)}
        </select>
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={direction} onChange={(event) => setDirection(event.target.value)}>
          <option value="INCREASE">Increase</option>
          <option value="DECREASE">Decrease</option>
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" type="number" min="1" value={qty} onChange={(event) => setQty(event.target.value)} />
        <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white">
          <SlidersHorizontal size={16} /> Adjust
        </button>
        <input className="focus-ring h-10 rounded-md border border-line px-3 md:col-span-5" placeholder="Reference" value={reference} onChange={(event) => setReference(event.target.value)} />
      </form>
      {error ? <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
      <div className="overflow-x-auto rounded-md border border-line bg-white">
        <table className="min-w-full divide-y divide-line text-sm">
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
    </>
  );
}

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Boxes, Download, History, IndianRupee, PackageX, Search } from "lucide-react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Product, StockHistory, StockMovementType } from "../types";
import { money, shortDate } from "../utils/format";

const movementTypes: StockMovementType[] = ["PURCHASE", "SALE", "CUSTOMER_RETURN", "SUPPLIER_RETURN", "DAMAGE", "MANUAL_ADJUSTMENT"];
const movementLabels: Record<StockMovementType, string> = { PURCHASE: "Purchase", SALE: "Sale", CUSTOMER_RETURN: "Customer Return", SUPPLIER_RETURN: "Supplier Return", DAMAGE: "Damage", MANUAL_ADJUSTMENT: "Manual Adjustment" };

export default function StockPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [movementType, setMovementType] = useState("");
  const [exporting, setExporting] = useState(false);
  const productsQuery = useQuery({ queryKey: ["inventory-products"], queryFn: () => api.get<Product[]>("/products?limit=500") });
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (movementType) params.set("movement_type", movementType);
  const historyQuery = useQuery({ queryKey: ["stock-history", productId, movementType], queryFn: () => api.get<StockHistory[]>(`/stock/history${params.toString() ? `?${params}` : ""}`) });
  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);
  const history = historyQuery.data ?? [];
  const visibleProducts = useMemo(() => { const value = search.trim().toLowerCase(); if (!value) return products; return products.filter((product) => [product.name, product.sku, product.barcode, product.brand?.name, product.category?.name].some((field) => field?.toLowerCase().includes(value))); }, [products, search]);
  const totalStock = products.reduce((sum, product) => sum + product.current_stock, 0);
  const inventoryValue = products.reduce((sum, product) => sum + Number(product.purchase_price) * product.current_stock, 0);
  const lowStock = products.filter((product) => product.current_stock > 0 && product.current_stock <= product.minimum_stock).length;
  const outOfStock = products.filter((product) => product.current_stock === 0).length;

  async function exportCsv() { setExporting(true); try { const blob = await api.getBlob(`/stock/history/export${params.toString() ? `?${params}` : ""}`); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "inventory-movements.csv"; anchor.click(); URL.revokeObjectURL(url); toast.success("Movement history exported"); } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to export movements"); } finally { setExporting(false); } }

  return (
    <>
      <PageHeader title="Inventory" subtitle="Current stock levels and complete movement history" actions={<Button type="button" variant="secondary" onClick={() => void exportCsv()} disabled={exporting}><Download size={16} /> {exporting ? "Exporting" : "Export CSV"}</Button>} />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="Total Stock" value={`${totalStock.toLocaleString("en-IN")} Units`} tone="teal" icon={Boxes} /><StatCard label="Inventory Value" value={money(inventoryValue)} tone="slate" icon={IndianRupee} /><StatCard label="Low Stock" value={lowStock} tone="amber" icon={AlertTriangle} /><StatCard label="Out of Stock" value={outOfStock} tone="rose" icon={PackageX} /></div>

      <section className="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white"><div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-lg font-semibold">Current Stock Levels</h2><p className="mt-1 text-sm text-slate-500">{visibleProducts.length} products</p></div><label className="flex h-11 min-w-0 items-center rounded-lg border border-slate-200 bg-white px-3 sm:w-80"><Search size={17} className="text-slate-400" /><input aria-label="Search current stock" className="min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Search products or barcode" value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>{productsQuery.isLoading ? <SkeletonRows rows={5} /> : productsQuery.error ? <ErrorState message={productsQuery.error instanceof Error ? productsQuery.error.message : "Unable to load stock"} /> : visibleProducts.length ? <div className="overflow-x-auto"><table className="min-w-[850px] divide-y divide-slate-100 text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Product</th><th className="px-5 py-3">Category</th><th className="px-5 py-3">SKU / Barcode</th><th className="px-5 py-3 text-right">Current</th><th className="px-5 py-3 text-right">Minimum</th><th className="px-5 py-3">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{visibleProducts.map((product) => <tr key={product.id}><td className="px-5 py-3"><div className="font-semibold text-slate-900">{product.name}</div><div className="text-xs text-slate-500">{product.size} · {product.color} · {product.brand?.name}</div></td><td className="px-5 py-3 text-slate-600">{product.category?.name} / {product.subcategory?.name}</td><td className="px-5 py-3"><div>{product.sku || "-"}</div><div className="text-xs text-slate-500">{product.barcode || "-"}</div></td><td className="px-5 py-3 text-right text-lg font-bold">{product.current_stock}</td><td className="px-5 py-3 text-right">{product.minimum_stock}</td><td className="px-5 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${product.current_stock === 0 ? "bg-red-100 text-red-700" : product.current_stock <= product.minimum_stock ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-700"}`}>{product.current_stock === 0 ? "Out of Stock" : product.current_stock <= product.minimum_stock ? "Low Stock" : "In Stock"}</span></td></tr>)}</tbody></table></div> : <EmptyState icon={Boxes} title="No products found" description="Products matching your search will appear here." />}</section>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white"><div className="grid gap-3 border-b border-slate-100 px-5 py-4 md:grid-cols-[minmax(0,1fr)_240px]"><div><h2 className="text-lg font-semibold">Inventory Movement</h2><p className="mt-1 text-sm text-slate-500">Every stock change with its reason, reference, user, and time</p></div><div className="grid gap-2 sm:grid-cols-2 md:grid-cols-1"><select className="field-input" value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">All products</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name} / {product.size} / {product.color}</option>)}</select><select className="field-input" value={movementType} onChange={(event) => setMovementType(event.target.value)}><option value="">All movement types</option>{movementTypes.map((type) => <option key={type} value={type}>{movementLabels[type]}</option>)}</select></div></div>{historyQuery.isLoading ? <SkeletonRows rows={6} /> : historyQuery.error ? <ErrorState message={historyQuery.error instanceof Error ? historyQuery.error.message : "Unable to load movement history"} /> : history.length ? <div className="overflow-x-auto"><table className="min-w-[980px] divide-y divide-slate-100 text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Type</th><th className="px-5 py-3">Product</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Stock</th><th className="px-5 py-3">Reference</th><th className="px-5 py-3">User</th><th className="px-5 py-3">Date</th></tr></thead><tbody className="divide-y divide-slate-100">{history.map((movement) => <tr key={movement.id}><td className="px-5 py-3"><StatusBadge value={movement.movement_type} /></td><td className="px-5 py-3"><div className="font-semibold">{movement.product?.name ?? "Product"}</div><div className="text-xs text-slate-500">{movement.product ? `${movement.product.size} · ${movement.product.color}` : movement.product_id}</div></td><td className="px-5 py-3 font-bold">{movement.after_stock < movement.before_stock ? "-" : "+"}{movement.qty}</td><td className="px-5 py-3 text-slate-600">{movement.before_stock} → {movement.after_stock}</td><td className="px-5 py-3 font-medium">{movement.reference || "-"}</td><td className="px-5 py-3">{movement.created_by_user?.full_name || "System"}</td><td className="px-5 py-3 text-slate-600">{shortDate(movement.movement_date)}</td></tr>)}</tbody></table></div> : <EmptyState icon={History} title="No inventory movements" description="Purchases, sales, returns, damage, and manual corrections will appear here." />}</section>
    </>
  );
}

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowDown, ArrowUp, ClipboardPenLine, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import BarcodeScannerInput from "../components/BarcodeScannerInput";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";
import VariantCorrectionPanel from "../components/VariantCorrectionPanel";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Product, ProductVariant, ProductVariantBarcode, StockHistory } from "../types";
import { money } from "../utils/format";

type AdjustmentType = "ADD_STOCK" | "REMOVE_STOCK" | "SET_COUNTED_QUANTITY";

interface VariantRow {
  product: Product;
  variant: ProductVariant;
}

function detail(row: VariantRow | null) {
  if (!row) return "";
  return [row.product.category?.name, row.product.brand?.name, row.variant.size || "Standard", row.variant.color].filter(Boolean).join(" / ");
}

export default function StockAdjustmentPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [variantId, setVariantId] = useState(searchParams.get("variant_id") ?? "");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [search, setSearch] = useState("");
  const [adjustmentType, setAdjustmentType] = useState<AdjustmentType>("ADD_STOCK");
  const [quantity, setQuantity] = useState("1");
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const productsQuery = useQuery({ queryKey: ["adjustment-products"], queryFn: () => api.get<Product[]>("/products?limit=500&is_active=true") });
  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);
  const variants = useMemo<VariantRow[]>(() => products.flatMap((product) => (product.variants ?? []).map((variant) => ({ product, variant }))), [products]);
  const selected = variants.find((row) => row.variant.id === variantId) ?? null;
  const categories = useMemo(() => Array.from(new Map(products.map((product) => product.category).filter(Boolean).map((category) => [category!.id, category!])).values()).sort((a, b) => a.name.localeCompare(b.name)), [products]);
  const brands = useMemo(() => Array.from(new Map(products.filter((product) => !categoryFilter || product.category_id === categoryFilter).map((product) => product.brand).filter(Boolean).map((brand) => [brand!.id, brand!])).values()).sort((a, b) => a.name.localeCompare(b.name)), [categoryFilter, products]);
  const filteredVariants = useMemo(() => {
    const value = search.trim().toLowerCase();
    return variants.filter((row) => {
      if (categoryFilter && row.product.category_id !== categoryFilter) return false;
      if (brandFilter && row.product.brand_id !== brandFilter) return false;
      if (!value) return true;
      return [row.product.name, row.product.category?.name, row.product.brand?.name, row.variant.size, row.variant.color, row.variant.barcode, row.variant.internal_sku].some((field) => field?.toLowerCase().includes(value));
    });
  }, [brandFilter, categoryFilter, search, variants]);
  const qty = Number(quantity || 0);
  const delta = selected ? adjustmentType === "ADD_STOCK" ? qty : adjustmentType === "REMOVE_STOCK" ? -qty : qty - selected.variant.current_stock : 0;
  const resultingStock = selected ? selected.variant.current_stock + delta : null;

  async function scanAdjustment(barcode: string, signal: AbortSignal) {
    const variant = await api.get<ProductVariantBarcode>(`/product-variants/by-barcode/${encodeURIComponent(barcode)}`, { signal });
    setVariantId(variant.variant_id); setQuantity(String(variant.package_quantity)); setError("");
    toast.success(`${variant.product_name} ${variant.size || "Standard"} selected`);
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("Select an exact product variant");
      if (!Number.isInteger(qty) || qty < 0 || (adjustmentType !== "SET_COUNTED_QUANTITY" && qty <= 0)) throw new Error("Quantity must be a valid whole number");
      if (!reference.trim()) throw new Error("Adjustment reason is required for audit history");
      if (resultingStock !== null && resultingStock < 0) throw new Error("Stock cannot become negative");
      const direction = delta >= 0 ? "INCREASE" : "DECREASE";
      const adjustedQty = adjustmentType === "SET_COUNTED_QUANTITY" ? qty : Math.abs(delta);
      return api.post<StockHistory>("/stock/adjustments", { product_id: selected.product.id, product_variant_id: selected.variant.id, adjustment_type: adjustmentType, reason: "MANUAL_ADJUSTMENT", direction, qty: adjustedQty, reference: reference.trim() });
    },
    onSuccess: () => {
      toast.success("Variant stock movement recorded");
      setVariantId(""); setQuantity("1"); setReference(""); setError("");
      for (const key of ["inventory-products", "adjustment-products", "stock-history", "products", "pos-variant-catalog", "sales-dashboard"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to adjust stock"; setError(message); toast.error(message); },
  });

  return <><PageHeader title="Stock Adjustment" subtitle="Use this to correct current physical stock by exact size, colour, barcode, and SKU" /><VariantCorrectionPanel products={products} /><div className="grid gap-6 xl:grid-cols-[minmax(0,760px)_minmax(280px,1fr)]"><section className="space-y-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-950"><div className="font-semibold">Use this to correct current physical stock.</div><p className="mt-1">This records a stock movement with before and after quantities. Product details, variant details, and barcode assignments remain separate catalogue actions.</p></div><BarcodeScannerInput label="Scan adjustment barcode" placeholder="Scan an exact variant barcode" onScan={scanAdjustment} /><div className="grid gap-3 sm:grid-cols-2"><label className="field-label">Category<select className="field-input mt-1" value={categoryFilter} onChange={(event) => { setCategoryFilter(event.target.value); setBrandFilter(""); }}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="field-label">Brand<select className="field-input mt-1" value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}><option value="">All brands</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label></div><label className="field-label">Search variants<div className="field-input mt-1 flex items-center gap-2"><Search size={16} className="text-slate-400" /><input className="min-w-0 flex-1 border-0 bg-transparent outline-none" placeholder="Product, size, colour, SKU, barcode" value={search} onChange={(event) => setSearch(event.target.value)} /></div></label><label className="field-label">Exact variant<span>*</span><select className="field-input" value={variantId} onChange={(event) => setVariantId(event.target.value)}><option value="">Select exact variant</option>{filteredVariants.map((row) => <option key={row.variant.id} value={row.variant.id}>{row.product.name} / {detail(row)} / {row.variant.barcode} / {row.variant.current_stock} in stock</option>)}</select></label>{selected ? <div className="rounded-lg bg-primary-50 p-3 text-sm text-primary-900"><strong>{selected.product.name}</strong><div>{detail(selected)}</div><div>Barcode: {selected.variant.barcode} · SKU: {selected.variant.internal_sku}</div><div>MRP: {selected.variant.mrp ? money(selected.variant.mrp) : "-"} · Selling: {money(selected.variant.selling_price)}</div></div> : null}<div><div className="mb-2 text-sm font-semibold text-slate-700">Adjustment type</div><div className="grid gap-3 sm:grid-cols-3"><button type="button" onClick={() => setAdjustmentType("ADD_STOCK")} className={`flex h-12 items-center justify-center gap-2 rounded-lg border font-semibold ${adjustmentType === "ADD_STOCK" ? "border-emerald-600 bg-emerald-50 text-emerald-700" : "border-slate-200 text-slate-500"}`}><ArrowUp size={18} /> Add</button><button type="button" onClick={() => setAdjustmentType("REMOVE_STOCK")} className={`flex h-12 items-center justify-center gap-2 rounded-lg border font-semibold ${adjustmentType === "REMOVE_STOCK" ? "border-red-500 bg-red-50 text-red-700" : "border-slate-200 text-slate-500"}`}><ArrowDown size={18} /> Remove</button><button type="button" onClick={() => setAdjustmentType("SET_COUNTED_QUANTITY")} className={`h-12 rounded-lg border font-semibold ${adjustmentType === "SET_COUNTED_QUANTITY" ? "border-teal-600 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-500"}`}>Set counted</button></div></div><label className="field-label">{adjustmentType === "SET_COUNTED_QUANTITY" ? "Counted quantity" : "Quantity"}<span>*</span><input className="field-input" type="number" min={adjustmentType === "SET_COUNTED_QUANTITY" ? 0 : 1} step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label className="field-label">Adjustment reason<span>*</span><input className="field-input" placeholder="Physical count, shelf correction, damaged item, owner correction" value={reference} onChange={(event) => setReference(event.target.value)} /></label>{error ? <ErrorState message={error} /> : null}<div className="flex justify-end border-t border-slate-100 pt-5"><Button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate()}><ClipboardPenLine size={17} /> {mutation.isPending ? "Recording" : "Record Movement"}</Button></div></section><aside className="h-fit rounded-lg border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold">Stock Preview</h2>{selected ? <div className="mt-4 space-y-3"><div><div className="font-semibold">{selected.product.name}</div><div className="text-sm text-slate-500">{detail(selected)}</div></div><div className="grid grid-cols-3 gap-3"><div className="rounded-lg bg-slate-50 p-4"><div className="text-xs text-slate-500">Current</div><div className="mt-1 text-2xl font-bold">{selected.variant.current_stock}</div></div><div className="rounded-lg bg-slate-50 p-4"><div className="text-xs text-slate-500">Change</div><div className={`mt-1 text-2xl font-bold ${delta < 0 ? "text-red-700" : "text-emerald-700"}`}>{delta > 0 ? "+" : ""}{delta}</div></div><div className={`rounded-lg p-4 ${resultingStock !== null && resultingStock < 0 ? "bg-red-50" : "bg-teal-50"}`}><div className="text-xs text-slate-500">After</div><div className={`mt-1 text-2xl font-bold ${resultingStock !== null && resultingStock < 0 ? "text-red-700" : "text-teal-800"}`}>{resultingStock}</div></div></div>{resultingStock !== null && resultingStock < 0 ? <div className="flex gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700"><AlertTriangle size={17} className="shrink-0" /> This adjustment would make stock negative.</div> : null}</div> : <p className="mt-3 text-sm text-slate-500">Select or scan an exact variant to preview the resulting stock level.</p>}</aside></div></>;
}

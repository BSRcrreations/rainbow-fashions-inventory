import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Boxes, Download, History, IndianRupee, PackageX, Pencil, RotateCcw, Search, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useAuth } from "../hooks/useAuth";
import type { Product, ProductVariant, StockHistory, StockMovementType, StockResetPreviewResponse, StockResetResponse, StockResetScope } from "../types";
import { money, shortDate } from "../utils/format";

const RESET_CONFIRMATION = "This will set the selected existing stock quantities to zero. Products, variants and barcodes will remain available.";
const movementTypes: StockMovementType[] = ["PURCHASE", "PURCHASE_VOID", "SALE", "SALE_EDIT_RETURN", "SALE_EDIT_DECREASE", "SALE_VOID", "CUSTOMER_RETURN", "SUPPLIER_RETURN", "DAMAGE", "MANUAL_ADJUSTMENT", "OPENING_STOCK", "STOCK_RESET_OUT", "STOCK_COUNT_IN", "STOCK_COUNT_OUT"];
const movementLabels: Record<StockMovementType, string> = { PURCHASE: "Purchase", PURCHASE_VOID: "Purchase void", SALE: "Sale", SALE_EDIT_RETURN: "Sale edit return", SALE_EDIT_DECREASE: "Sale edit decrease", SALE_VOID: "Sale void", CUSTOMER_RETURN: "Customer Return", SUPPLIER_RETURN: "Supplier Return", DAMAGE: "Damage", MANUAL_ADJUSTMENT: "Manual Adjustment", OPENING_STOCK: "Opening Stock", STOCK_RESET_OUT: "Stock reset", STOCK_COUNT_IN: "Physical Count In", STOCK_COUNT_OUT: "Physical Count Out" };

interface VariantRow {
  product: Product;
  variant: ProductVariant;
}

function requestId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `stock-reset-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function statusClass(stock: number, minimum: number) {
  if (stock === 0) return "bg-red-100 text-red-700";
  if (minimum > 0 && stock <= minimum) return "bg-amber-100 text-amber-800";
  return "bg-emerald-100 text-emerald-700";
}

function stockLabel(stock: number, minimum: number) {
  if (stock === 0) return "Out of stock";
  if (minimum > 0 && stock <= minimum) return "Low stock";
  return "In stock";
}

export default function StockPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [sizeFilter, setSizeFilter] = useState("");
  const [stockMode, setStockMode] = useState<"variants" | "grouped">("variants");
  const [selectedVariantIds, setSelectedVariantIds] = useState<Set<string>>(new Set());
  const [productId, setProductId] = useState("");
  const [movementType, setMovementType] = useState("");
  const [exporting, setExporting] = useState(false);
  const [correction, setCorrection] = useState<StockHistory | null>(null);
  const [correctQuantity, setCorrectQuantity] = useState("");
  const [correctionReason, setCorrectionReason] = useState("DATA_ENTRY_MISTAKE");
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [resetOpen, setResetOpen] = useState(false);
  const [resetScope, setResetScope] = useState<StockResetScope>("SELECTED_VARIANTS");
  const [resetProductId, setResetProductId] = useState("");
  const [resetCategoryId, setResetCategoryId] = useState("");
  const [resetBrandId, setResetBrandId] = useState("");
  const [ownerPassword, setOwnerPassword] = useState("");
  const [resetConfirmed, setResetConfirmed] = useState(false);
  const [resetPreview, setResetPreview] = useState<StockResetPreviewResponse | null>(null);

  const productsQuery = useQuery({ queryKey: ["inventory-products"], queryFn: () => api.get<Product[]>("/products?limit=500") });
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (movementType) params.set("movement_type", movementType);
  const historyQuery = useQuery({ queryKey: ["stock-history", productId, movementType], queryFn: () => api.get<StockHistory[]>(`/stock/history${params.toString() ? `?${params}` : ""}`) });
  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);
  const history = historyQuery.data ?? [];
  const variantRows = useMemo<VariantRow[]>(() => products.flatMap((product) => (product.variants ?? []).map((variant) => ({ product, variant }))), [products]);
  const categories = useMemo(() => Array.from(new Map(products.map((product) => product.category).filter(Boolean).map((category) => [category!.id, category!])).values()).sort((a, b) => a.name.localeCompare(b.name)), [products]);
  const brands = useMemo(() => Array.from(new Map(products.filter((product) => !categoryFilter || product.category_id === categoryFilter).map((product) => product.brand).filter(Boolean).map((brand) => [brand!.id, brand!])).values()).sort((a, b) => a.name.localeCompare(b.name)), [categoryFilter, products]);
  const sizes = useMemo(() => Array.from(new Set(variantRows.map((row) => row.variant.size).filter((value): value is string => Boolean(value)))).sort(), [variantRows]);
  const visibleRows = useMemo(() => {
    const value = search.trim().toLowerCase();
    return variantRows.filter(({ product, variant }) => {
      if (categoryFilter && product.category_id !== categoryFilter) return false;
      if (brandFilter && product.brand_id !== brandFilter) return false;
      if (sizeFilter && variant.size !== sizeFilter) return false;
      if (!value) return true;
      return [product.name, product.sku, product.barcode, product.brand?.name, product.category?.name, variant.size, variant.color, variant.barcode, ...(variant.barcodes ?? []), variant.internal_sku, variant.manufacturer_sku].some((field) => field?.toLowerCase().includes(value));
    });
  }, [brandFilter, categoryFilter, search, sizeFilter, variantRows]);
  const totalStock = variantRows.reduce((sum, row) => sum + row.variant.current_stock, 0);
  const inventoryValue = variantRows.reduce((sum, row) => sum + Number(row.variant.average_cost || row.variant.last_purchase_cost || row.product.purchase_price) * row.variant.current_stock, 0);
  const lowStock = variantRows.filter((row) => row.variant.current_stock > 0 && row.product.minimum_stock > 0 && row.variant.current_stock <= row.product.minimum_stock).length;
  const outOfStock = variantRows.filter((row) => row.variant.current_stock === 0).length;
  const canCorrect = user?.role === "OWNER" || user?.role === "MANAGER";
  const canReset = user?.role === "OWNER";

  const resetPayload = () => ({
    scope: resetScope,
    variant_ids: resetScope === "SELECTED_VARIANTS" ? Array.from(selectedVariantIds) : [],
    product_id: resetScope === "PRODUCT" ? resetProductId || null : null,
    category_id: resetScope === "CATEGORY" ? resetCategoryId || null : null,
    brand_id: resetScope === "BRAND" ? resetBrandId || null : null,
  });

  const previewMutation = useMutation({
    mutationFn: () => {
      if (resetScope === "SELECTED_VARIANTS" && selectedVariantIds.size === 0) throw new Error("Select at least one variant");
      const id = requestId();
      return api.post<StockResetPreviewResponse>("/stock/reset-preview", resetPayload(), { "X-Request-ID": id });
    },
    onSuccess: setResetPreview,
    onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to preview reset"),
  });
  const resetMutation = useMutation({
    mutationFn: () => {
      if (!resetPreview) throw new Error("Preview the reset first");
      if (!resetConfirmed) throw new Error("Confirm that products and barcodes will be preserved");
      return api.post<StockResetResponse>("/stock/reset", { ...resetPayload(), confirmation: RESET_CONFIRMATION, owner_password: ownerPassword || null }, { "Idempotency-Key": resetPreview.request_id, "X-Request-ID": resetPreview.request_id });
    },
    onSuccess: (result) => {
      toast.success(result.already_completed ? "Reset was already completed for this request" : `Reset ${result.total_pieces} pieces to zero`);
      setResetOpen(false); setResetPreview(null); setSelectedVariantIds(new Set()); setOwnerPassword(""); setResetConfirmed(false);
      for (const key of ["inventory-products", "stock-history", "products", "pos-variant-catalog", "sales-dashboard"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to reset stock"),
  });
  const correctionMutation = useMutation({ mutationFn: () => { if (!correction) throw new Error("Select a stock transaction"); const quantity = Number(correctQuantity); if (!Number.isInteger(quantity) || quantity < 0) throw new Error("Correct quantity must be zero or more"); if (correctionReason === "OTHER" && !correctionNotes.trim()) throw new Error("Notes are required when reason is Other"); return api.post<StockHistory>(`/stock/transactions/${correction.id}/correct`, { correct_quantity: quantity, reason: correctionReason, notes: correctionNotes || null }); }, onSuccess: () => { toast.success("Original record preserved. The stock correction was recorded."); setCorrection(null); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); void queryClient.invalidateQueries({ queryKey: ["inventory-products"] }); }, onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to correct stock entry") });

  function toggleVariant(id: string, checked: boolean) { setSelectedVariantIds((current) => { const next = new Set(current); if (checked) next.add(id); else next.delete(id); return next; }); }
  function openReset() { setResetScope(selectedVariantIds.size ? "SELECTED_VARIANTS" : "ALL_CURRENT_STOCK"); setResetPreview(null); setResetConfirmed(false); setOwnerPassword(""); setResetOpen(true); }
  async function exportCsv() { setExporting(true); try { const blob = await api.getBlob(`/stock/history/export${params.toString() ? `?${params}` : ""}`); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "inventory-movements.csv"; anchor.click(); URL.revokeObjectURL(url); toast.success("Movement history exported"); } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to export movements"); } finally { setExporting(false); } }

  return (
    <>
      <PageHeader title="Inventory" subtitle="Variant-level stock, corrections, and owner reset controls" actions={<div className="flex flex-wrap gap-2">{canReset ? <Button type="button" variant="destructive" onClick={openReset}><RotateCcw size={16} /> Reset Existing Stock</Button> : null}<Button type="button" variant="secondary" onClick={() => void exportCsv()} disabled={exporting}><Download size={16} /> {exporting ? "Exporting" : "Export CSV"}</Button></div>} />
      <section className="mb-6 rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-950">
        <div className="font-semibold">Current stock is transaction-controlled.</div>
        <p className="mt-1">Use Stock Adjustment to correct current physical stock. Confirmed records are locked; create a correction transaction to fix a mistake while preserving audit history.</p>
      </section>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="Physical Stock" value={`${totalStock.toLocaleString("en-IN")} Units`} tone="teal" icon={Boxes} /><StatCard label="Inventory Value" value={money(inventoryValue)} tone="slate" icon={IndianRupee} /><StatCard label="Low Variants" value={lowStock} tone="amber" icon={AlertTriangle} /><StatCard label="Out of Stock" value={outOfStock} tone="rose" icon={PackageX} /></div>

      <section className="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="grid gap-3 border-b border-slate-100 px-5 py-4 xl:grid-cols-[minmax(0,1fr)_auto]">
          <div><h2 className="text-lg font-semibold">Current Stock Levels</h2><p className="mt-1 text-sm text-slate-500">{stockMode === "variants" ? `${visibleRows.length} size variants` : `${products.length} grouped products`}</p></div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-slate-200 p-1"><button type="button" className={`h-9 rounded-md px-3 text-sm font-semibold ${stockMode === "variants" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => setStockMode("variants")}>Variants</button><button type="button" className={`h-9 rounded-md px-3 text-sm font-semibold ${stockMode === "grouped" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => setStockMode("grouped")}>Grouped</button></div>
            <label className="flex h-11 min-w-0 items-center rounded-lg border border-slate-200 bg-white px-3 sm:w-80"><Search size={17} className="text-slate-400" /><input aria-label="Search current stock" className="min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Search product, size, SKU or barcode" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          </div>
          <div className="flex flex-wrap gap-2 xl:col-span-2">
            <select className="field-input h-10 w-full sm:w-48" value={categoryFilter} onChange={(event) => { setCategoryFilter(event.target.value); setBrandFilter(""); }}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select>
            <select className="field-input h-10 w-full sm:w-48" value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}><option value="">All brands</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select>
            <select className="field-input h-10 w-full sm:w-40" value={sizeFilter} onChange={(event) => setSizeFilter(event.target.value)}><option value="">All sizes</option>{sizes.map((size) => <option key={size} value={size}>{size}</option>)}</select>
            <Button type="button" variant="ghost" onClick={() => { setSearch(""); setCategoryFilter(""); setBrandFilter(""); setSizeFilter(""); }}>Clear filters</Button>
          </div>
        </div>
        {productsQuery.isLoading ? <SkeletonRows rows={5} /> : productsQuery.error ? <ErrorState message={productsQuery.error instanceof Error ? productsQuery.error.message : "Unable to load stock"} /> : stockMode === "variants" ? (
          visibleRows.length ? <div className="overflow-x-auto"><table className="min-w-[1280px] divide-y divide-slate-100 text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr>{canReset ? <th className="w-12 px-5 py-3"><span className="sr-only">Select</span></th> : null}<th className="px-5 py-3">Product</th><th className="px-5 py-3">Category</th><th className="px-5 py-3">Brand</th><th className="px-5 py-3">Size</th><th className="px-5 py-3">Colour</th><th className="px-5 py-3">Barcode / SKU</th><th className="px-5 py-3 text-right">Cost</th><th className="px-5 py-3 text-right">MRP</th><th className="px-5 py-3 text-right">Selling</th><th className="px-5 py-3 text-right">Physical</th><th className="px-5 py-3 text-right">Reserved</th><th className="px-5 py-3 text-right">Available</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{visibleRows.map(({ product, variant }) => <tr key={variant.id} className="hover:bg-slate-50">{canReset ? <td className="px-5 py-3"><input aria-label={`Select ${product.name} ${variant.size ?? ""}`} type="checkbox" checked={selectedVariantIds.has(variant.id)} onChange={(event) => toggleVariant(variant.id, event.target.checked)} /></td> : null}<td className="px-5 py-3 font-semibold text-slate-900">{product.name}</td><td className="px-5 py-3 text-slate-600">{product.category?.name ?? "-"}</td><td className="px-5 py-3 text-slate-600">{product.brand?.name ?? "Unbranded"}</td><td className="px-5 py-3 font-semibold">{variant.size || "Standard"}</td><td className="px-5 py-3">{variant.color || "-"}</td><td className="px-5 py-3"><div>{variant.barcode}</div><div className="text-xs text-slate-500">{variant.internal_sku}</div></td><td className="px-5 py-3 text-right">{money(variant.average_cost || variant.last_purchase_cost)}</td><td className="px-5 py-3 text-right">{variant.mrp ? money(variant.mrp) : "-"}</td><td className="px-5 py-3 text-right font-semibold">{money(variant.selling_price)}</td><td className="px-5 py-3 text-right text-lg font-bold">{variant.current_stock}</td><td className="px-5 py-3 text-right">0</td><td className="px-5 py-3 text-right font-semibold">{variant.current_stock}</td><td className="px-5 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(variant.current_stock, product.minimum_stock)}`}>{stockLabel(variant.current_stock, product.minimum_stock)}</span></td><td className="px-5 py-3"><Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/stock-adjustment?variant_id=${variant.id}`)}><Pencil size={14} /> Adjust</Button></td></tr>)}</tbody></table></div> : <EmptyState icon={Boxes} title="No variants found" description="Try another category, brand, size, barcode, or SKU." />
        ) : products.length ? <div className="overflow-x-auto"><table className="min-w-[900px] divide-y divide-slate-100 text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Product</th><th className="px-5 py-3">Category</th><th className="px-5 py-3">Brand</th><th className="px-5 py-3 text-right">Variants</th><th className="px-5 py-3 text-right">Total stock</th><th className="px-5 py-3">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{products.map((product) => { const total = (product.variants ?? []).reduce((sum, variant) => sum + variant.current_stock, 0); return <tr key={product.id}><td className="px-5 py-3 font-semibold">{product.name}</td><td className="px-5 py-3">{product.category?.name ?? "-"}</td><td className="px-5 py-3">{product.brand?.name ?? "Unbranded"}</td><td className="px-5 py-3 text-right">{product.variants?.length ?? 0}</td><td className="px-5 py-3 text-right text-lg font-bold">{total}</td><td className="px-5 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(total, product.minimum_stock)}`}>{stockLabel(total, product.minimum_stock)}</span></td></tr>; })}</tbody></table></div> : <EmptyState icon={Boxes} title="No products found" description="Products matching your search will appear here." />}
      </section>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white"><div className="grid gap-3 border-b border-slate-100 px-5 py-4 md:grid-cols-[minmax(0,1fr)_240px]"><div><h2 className="text-lg font-semibold">Inventory Movement</h2><p className="mt-1 text-sm text-slate-500">Every stock change with its reason, reference, user, and time</p></div><div className="grid gap-2 sm:grid-cols-2 md:grid-cols-1"><select className="field-input" value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">All products</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select><select className="field-input" value={movementType} onChange={(event) => setMovementType(event.target.value)}><option value="">All movement types</option>{movementTypes.map((type) => <option key={type} value={type}>{movementLabels[type]}</option>)}</select></div></div>{historyQuery.isLoading ? <SkeletonRows rows={6} /> : historyQuery.error ? <ErrorState message={historyQuery.error instanceof Error ? historyQuery.error.message : "Unable to load movement history"} /> : history.length ? <div className="overflow-x-auto"><table className="min-w-[1040px] divide-y divide-slate-100 text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Type</th><th className="px-5 py-3">Product</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Stock</th><th className="px-5 py-3">Reference</th><th className="px-5 py-3">User</th><th className="px-5 py-3">Date</th><th className="px-5 py-3">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{history.map((movement) => <tr key={movement.id}><td className="px-5 py-3"><StatusBadge value={movement.movement_type} /></td><td className="px-5 py-3"><div className="font-semibold">{movement.product?.name ?? "Product"}</div><div className="text-xs text-slate-500">{movement.product_variant_id ?? movement.product_id}</div></td><td className="px-5 py-3 font-bold">{movement.after_stock < movement.before_stock ? "-" : "+"}{movement.qty}</td><td className="px-5 py-3 text-slate-600">{movement.before_stock} {"->"} {movement.after_stock}</td><td className="px-5 py-3 font-medium">{movement.reference || "-"}</td><td className="px-5 py-3">{movement.created_by_user?.full_name || "System"}</td><td className="px-5 py-3 text-slate-600">{shortDate(movement.movement_date)}</td><td className="px-5 py-3">{canCorrect && !movement.correction_of_id ? <Button type="button" variant="secondary" size="sm" onClick={() => { setCorrection(movement); setCorrectQuantity(String(movement.after_stock)); setCorrectionReason("DATA_ENTRY_MISTAKE"); setCorrectionNotes(""); }}><Pencil size={14} /> Correct entry</Button> : "-"}</td></tr>)}</tbody></table></div> : <EmptyState icon={History} title="No inventory movements" description="Purchases, sales, returns, damage, and manual corrections will appear here." />}</section>

      <Dialog open={resetOpen} onClose={() => setResetOpen(false)} title="Reset Existing Stock to Zero" description="Preview exact variants before the owner confirms the reset." maxWidth="xl">
        <div className="space-y-5">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><div className="flex items-center gap-2 font-semibold"><ShieldAlert size={17} /> Owner-controlled stock reset</div><p className="mt-1">{RESET_CONFIRMATION}</p></div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <label className="field-label">Scope<select className="field-input mt-1" value={resetScope} onChange={(event) => { setResetScope(event.target.value as StockResetScope); setResetPreview(null); }}><option value="SELECTED_VARIANTS">Selected variants</option><option value="CATEGORY">Category</option><option value="BRAND">Brand</option><option value="PRODUCT">Product</option><option value="ALL_OPENING_STOCK">Reset all opening stock</option><option value="ALL_CURRENT_STOCK">All current stock</option></select></label>
            {resetScope === "CATEGORY" ? <label className="field-label">Category<select className="field-input mt-1" value={resetCategoryId} onChange={(event) => { setResetCategoryId(event.target.value); setResetPreview(null); }}><option value="">Select category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label> : null}
            {resetScope === "BRAND" ? <label className="field-label">Brand<select className="field-input mt-1" value={resetBrandId} onChange={(event) => { setResetBrandId(event.target.value); setResetPreview(null); }}><option value="">Select brand</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label> : null}
            {resetScope === "PRODUCT" ? <label className="field-label">Product<select className="field-input mt-1" value={resetProductId} onChange={(event) => { setResetProductId(event.target.value); setResetPreview(null); }}><option value="">Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label> : null}
            <div className="flex items-end"><Button type="button" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>{previewMutation.isPending ? "Previewing" : "Preview reset"}</Button></div>
          </div>
          {resetScope === "SELECTED_VARIANTS" ? <p className="text-sm text-slate-600">{selectedVariantIds.size} selected variant{selectedVariantIds.size === 1 ? "" : "s"} will be previewed.</p> : null}
          {resetPreview ? <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-4"><StatCard label="Products" value={resetPreview.total_products} tone="slate" icon={Boxes} /><StatCard label="Variants" value={resetPreview.total_variants} tone="teal" icon={Boxes} /><StatCard label="Pieces reset" value={resetPreview.total_pieces} tone="rose" icon={RotateCcw} /><StatCard label="Value affected" value={money(resetPreview.total_inventory_value)} tone="amber" icon={IndianRupee} /></div><div className="overflow-x-auto rounded-lg border border-slate-200"><table className="min-w-[960px] divide-y divide-slate-100 text-sm"><thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Product</th><th className="px-4 py-3">Brand</th><th className="px-4 py-3">Category</th><th className="px-4 py-3">Size</th><th className="px-4 py-3">Colour</th><th className="px-4 py-3">Barcode</th><th className="px-4 py-3 text-right">Current</th><th className="px-4 py-3 text-right">Reverse</th><th className="px-4 py-3 text-right">After</th></tr></thead><tbody className="divide-y divide-slate-100">{resetPreview.variants.map((item) => <tr key={item.variant_id}><td className="px-4 py-3 font-semibold">{item.product}</td><td className="px-4 py-3">{item.brand ?? "Unbranded"}</td><td className="px-4 py-3">{item.category ?? "-"}</td><td className="px-4 py-3">{item.size ?? "Standard"}</td><td className="px-4 py-3">{item.color ?? "-"}</td><td className="px-4 py-3">{item.barcode}</td><td className="px-4 py-3 text-right font-bold">{item.current_stock}</td><td className="px-4 py-3 text-right text-rose-700">{item.reset_quantity}</td><td className="px-4 py-3 text-right font-bold">{item.resulting_stock}</td></tr>)}</tbody></table></div><label className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 text-sm"><input className="mt-1" type="checkbox" checked={resetConfirmed} onChange={(event) => setResetConfirmed(event.target.checked)} /><span>{RESET_CONFIRMATION}</span></label><label className="field-label">Owner password <span className="text-slate-400">if configured</span><input className="field-input mt-1" type="password" value={ownerPassword} onChange={(event) => setOwnerPassword(event.target.value)} autoComplete="current-password" /></label><div className="flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setResetOpen(false)}>Cancel</Button><Button type="button" variant="destructive" disabled={!resetConfirmed || resetMutation.isPending || resetPreview.total_variants === 0} onClick={() => resetMutation.mutate()}>{resetMutation.isPending ? "Resetting" : "Reset stock to zero"}</Button></div></div> : null}
        </div>
      </Dialog>

      <Dialog open={Boolean(correction)} onClose={() => setCorrection(null)} title="Correct stock entry" description="The original transaction will be preserved. A new correcting movement will be recorded.">{correction ? <div className="space-y-4"><div className="rounded-lg bg-slate-50 p-3 text-sm"><strong>{correction.product?.name ?? "Product"}</strong><div>Original stock: {correction.before_stock} {"->"} {correction.after_stock}</div><div>Original movement: {movementLabels[correction.movement_type]}</div></div><label className="field-label">Correct quantity<input className="field-input mt-1" min="0" type="number" value={correctQuantity} onChange={(event) => setCorrectQuantity(event.target.value)} /></label><p className="text-sm text-muted">A correction of {(Number(correctQuantity || 0) - correction.after_stock) > 0 ? "+" : ""}{Number(correctQuantity || 0) - correction.after_stock} units will be recorded.</p><label className="field-label">Reason<select className="field-input mt-1" value={correctionReason} onChange={(event) => setCorrectionReason(event.target.value)}><option value="DATA_ENTRY_MISTAKE">Data-entry mistake</option><option value="DAMAGED_STOCK">Damaged stock</option><option value="MISSING_STOCK">Missing stock</option><option value="DUPLICATE_OPENING_STOCK">Duplicate opening stock</option><option value="INCORRECT_BARCODE_ASSIGNMENT">Incorrect barcode assignment</option><option value="INCORRECT_VARIANT_SELECTED">Incorrect variant selected</option><option value="TEST_DATA">Test data</option><option value="OTHER">Other</option></select></label><label className="field-label">Notes {correctionReason === "OTHER" ? "(required)" : "(optional)"}<textarea className="field-input mt-1 h-20 py-2" value={correctionNotes} onChange={(event) => setCorrectionNotes(event.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setCorrection(null)}>Cancel</Button><Button type="button" disabled={correctionMutation.isPending} onClick={() => correctionMutation.mutate()}>{correctionMutation.isPending ? "Recording" : "Record correction"}</Button></div></div> : null}</Dialog>
    </>
  );
}

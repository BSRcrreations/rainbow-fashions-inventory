import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ScanLine } from "lucide-react";
import { ApiError, api } from "../api/client";
import type { CategoryHierarchy, Product, ProductVariant, StockScanSession } from "../types";
import Dialog from "./Dialog";
import ErrorState from "./ErrorState";
import { Button } from "./ui/button";

type SharedTarget = { variant_id: string; product_id: string; product_name: string; brand_name?: string | null; size?: string | null; color?: string | null; current_stock: number };

interface Props {
  session: StockScanSession;
  initialBarcode?: string;
  canManageCatalog: boolean;
  onSaved: (session: StockScanSession) => void;
}

function variantLabel(variant: ProductVariant) { return [variant.size || "Standard", variant.color].filter(Boolean).join(" · "); }

export default function ProductFirstStockEntry({ session, initialBarcode = "", canManageCatalog, onSaved }: Props) {
  const queryClient = useQueryClient();
  const [categoryId, setCategoryId] = useState(session.default_category_id ?? "");
  const [brandId, setBrandId] = useState(session.default_brand_id ?? "");
  const [product, setProduct] = useState<Product | null>(null);
  const [variant, setVariant] = useState<ProductVariant | null>(null);
  const [barcode, setBarcode] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [quantityMode, setQuantityMode] = useState<"INCREMENT" | "QUANTITY_ENTRY">("INCREMENT");
  const [productDialog, setProductDialog] = useState(false);
  const [variantDialog, setVariantDialog] = useState(false);
  const [categoryDialog, setCategoryDialog] = useState(false);
  const [brandDialog, setBrandDialog] = useState(false);
  const [name, setName] = useState("");
  const [size, setSize] = useState("");
  const [color, setColor] = useState("");
  const [mrp, setMrp] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const [purchaseCost, setPurchaseCost] = useState("");
  const [catalogName, setCatalogName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [sharedConfirmation, setSharedConfirmation] = useState<{ barcode: string; targets: SharedTarget[] } | null>(null);
  const [conflict, setConflict] = useState<SharedTarget | null>(null);

  useEffect(() => { if (initialBarcode) setBarcode(initialBarcode); }, [initialBarcode]);

  const hierarchyQuery = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy") });
  const categories = hierarchyQuery.data ?? [];
  const selectedCategory = categories.find((item) => item.id === categoryId);
  const brands = selectedCategory?.brands.filter((item) => item.is_active) ?? [];
  const productsQuery = useQuery({
    queryKey: ["stock-product-first-products", categoryId, brandId],
    queryFn: () => api.get<Product[]>(`/products?category_id=${encodeURIComponent(categoryId)}&brand_id=${encodeURIComponent(brandId)}&limit=100`),
    enabled: Boolean(categoryId && brandId),
  });
  const products = productsQuery.data ?? [];
  const selectedVariantSummary = useMemo(() => variant ? { size: variant.size || "Standard", color: variant.color, stock: variant.current_stock } : null, [variant]);

  function chooseCategory(next: string) { setCategoryId(next); setBrandId(""); setProduct(null); setVariant(null); setError(""); }
  function chooseProduct(next: Product) { setProduct(next); setVariant(null); setError(""); }
  function chooseVariant(next: ProductVariant) { setVariant(next); setError(""); setConflict(null); }
  function priceNumber(value: string) { const amount = Number(value); return Number.isFinite(amount) && amount >= 0 ? amount : null; }

  async function createCategory() {
    if (!catalogName.trim()) { setError("Enter a category name."); return; }
    setPending(true); setError("");
    try {
      const category = await api.post<{ id: string }>("/categories", { name: catalogName.trim() });
      await api.post("/subcategories", { category_id: category.id, name: "General" });
      setCategoryId(category.id); setBrandId(""); setCategoryDialog(false); setCatalogName("");
      await hierarchyQuery.refetch();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to add category"); } finally { setPending(false); }
  }

  async function createBrand() {
    if (!catalogName.trim()) { setError("Enter a brand name."); return; }
    setPending(true); setError("");
    try {
      const brand = await api.post<{ id: string }>("/brands", { category_id: categoryId, name: catalogName.trim() });
      setBrandId(brand.id); setBrandDialog(false); setCatalogName("");
      await hierarchyQuery.refetch();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to add brand"); } finally { setPending(false); }
  }

  async function createProduct(event: FormEvent) {
    event.preventDefault();
    const subcategory = selectedCategory?.subcategories.find((item) => item.is_active);
    const cost = priceNumber(purchaseCost); const selling = priceNumber(sellingPrice); const priceMrp = mrp.trim() ? priceNumber(mrp) : null;
    if (!name.trim() || !subcategory || cost === null || selling === null || (mrp.trim() && priceMrp === null)) { setError("Enter product name, cost, selling price, and valid MRP where used."); return; }
    setPending(true); setError("");
    try {
      const created = await api.post<Product>("/products", { category_id: categoryId, subcategory_id: subcategory.id, brand_id: brandId, name: name.trim(), purchase_price: cost, selling_price: selling, pricing_type: priceMrp === null ? "OWN_PRICE" : "MRP", mrp: priceMrp, current_stock: 0, minimum_stock: 0, product_date: new Date().toISOString().slice(0, 10), colors: [], sizes: [] });
      setProduct(created); setVariant(null); setProductDialog(false); setName("");
      await queryClient.invalidateQueries({ queryKey: ["stock-product-first-products"] });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to create product"); } finally { setPending(false); }
  }

  async function createVariant(event: FormEvent) {
    event.preventDefault();
    if (!product || (!size.trim() && !color.trim())) { setError("Enter a size or colour for the exact variant."); return; }
    const cost = priceNumber(purchaseCost); const selling = priceNumber(sellingPrice); const priceMrp = mrp.trim() ? priceNumber(mrp) : null;
    if (cost === null || selling === null || (mrp.trim() && priceMrp === null)) { setError("Enter valid variant prices."); return; }
    setPending(true); setError("");
    try {
      const [sku, generatedBarcode] = await Promise.all([api.get<{ value: string }>("/products/generate-code?kind=sku"), api.get<{ value: string }>("/products/generate-code?kind=barcode")]);
      const created = await api.post<ProductVariant>("/product-variants/details", { product_id: product.id, size: size.trim() || null, color: color.trim() || null, internal_sku: sku.value, barcode: generatedBarcode.value, mrp: priceMrp, selling_price: selling, purchase_cost: cost });
      const nextProduct = { ...product, variants: [...product.variants, created] };
      setProduct(nextProduct); setVariant(created); setVariantDialog(false); setSize(""); setColor("");
      await queryClient.invalidateQueries({ queryKey: ["stock-product-first-products"] });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to add variant"); } finally { setPending(false); }
  }

  async function stage(confirmShared = false) {
    const count = quantityMode === "INCREMENT" ? 1 : Number(quantity);
    if (!variant || !barcode.trim() || !Number.isInteger(count) || count < 1) { setError("Select an exact variant, scan a barcode, and enter a whole quantity."); return; }
    setPending(true); setError(""); setConflict(null);
    try {
      const next = await api.post<StockScanSession>(`/stock-scan/sessions/${session.id}/stage-variant`, { product_variant_id: variant.id, barcode: barcode.trim(), quantity: count, confirm_shared_barcode: confirmShared });
      onSaved(next); setSharedConfirmation(null); setBarcode(""); setQuantity("1");
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "SHARED_BARCODE_CONFIRMATION_REQUIRED") {
        const details = cause.details ?? {}; setSharedConfirmation({ barcode: typeof details.barcode === "string" ? details.barcode : barcode, targets: Array.isArray(details.targets) ? details.targets as SharedTarget[] : [] });
      } else if (cause instanceof ApiError && cause.code === "BARCODE_PRODUCT_CONFLICT") {
        const existing = cause.details?.existing; if (existing && typeof existing === "object") setConflict(existing as SharedTarget);
      }
      setError(cause instanceof Error ? cause.message : "Unable to stage stock");
    } finally { setPending(false); }
  }

  return <section className="ds-surface space-y-5 p-4 sm:p-5" data-testid="product-first-entry">
    <div><h2 className="text-lg font-semibold">Select Product First</h2><p className="mt-1 text-sm text-muted">Choose the exact item before scanning its manufacturer barcode. Nothing here changes inventory until Review and Confirm Stock.</p></div>
    <div className="grid gap-4 lg:grid-cols-2">
      <label className="field-label">Step 1 — Category<select className="field-input mt-1" value={categoryId} onChange={(event) => chooseCategory(event.target.value)}><option value="">Select category</option>{categories.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <div className="flex items-end gap-2"><label className="field-label flex-1">Step 2 — Brand<select className="field-input mt-1" disabled={!categoryId} value={brandId} onChange={(event) => { setBrandId(event.target.value); setProduct(null); setVariant(null); }}><option value="">{categoryId ? "Select brand" : "Select category first"}</option>{brands.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{canManageCatalog && categoryId ? <Button type="button" variant="secondary" onClick={() => { setCatalogName(""); setBrandDialog(true); }}><Plus size={15} /> Add Brand</Button> : null}</div>
      {canManageCatalog ? <Button type="button" className="justify-self-start" variant="secondary" onClick={() => { setCatalogName(""); setCategoryDialog(true); }}><Plus size={15} /> Add Category</Button> : null}
    </div>
    {categoryId && brandId ? <section className="rounded-xl border border-border p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">Step 3 — Product</h3><p className="text-sm text-muted">Choose the product family/style.</p></div>{canManageCatalog ? <Button type="button" onClick={() => { setName(""); setProductDialog(true); }}><Plus size={15} /> Create Product</Button> : null}</div><div className="mt-3 grid gap-2 sm:grid-cols-2">{products.map((item) => <button key={item.id} type="button" onClick={() => chooseProduct(item)} className={`rounded-lg border p-3 text-left ${product?.id === item.id ? "border-primary-500 bg-primary-50" : "border-border hover:bg-slate-50"}`}><strong>{item.name}</strong><span className="mt-1 block text-xs text-muted">{item.variants.length} variant{item.variants.length === 1 ? "" : "s"}</span></button>)}{!products.length && !productsQuery.isLoading ? <p className="text-sm text-muted">No matching products yet. Create the style once, then add its exact variants.</p> : null}</div></section> : null}
    {product ? <section className="rounded-xl border border-border p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">Step 4 — Variant</h3><p className="text-sm text-muted">{product.name} · choose the exact size and colour.</p></div>{canManageCatalog ? <Button type="button" onClick={() => { const first = product.variants[0]; setMrp(first?.mrp ? String(first.mrp) : ""); setSellingPrice(first ? String(first.selling_price) : sellingPrice); setPurchaseCost(first ? String(first.last_purchase_cost) : purchaseCost); setVariantDialog(true); }}><Plus size={15} /> Add Variant</Button> : null}</div><div className="mt-3 flex flex-wrap gap-2">{product.variants.filter((item) => item.is_active).map((item) => <button key={item.id} type="button" onClick={() => chooseVariant(item)} className={`rounded-lg border px-3 py-2 text-left text-sm ${variant?.id === item.id ? "border-primary-500 bg-primary-50" : "border-border hover:bg-slate-50"}`}><strong>{variantLabel(item)}</strong><span className="ml-2 text-xs text-muted">Stock {item.current_stock}</span></button>)}{!product.variants.length ? <p className="text-sm text-muted">Add the first exact variant. This creates zero stock.</p> : null}</div></section> : null}
    {variant && selectedVariantSummary ? <section className="rounded-xl border border-primary-200 bg-primary-50/60 p-4"><div className="flex gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary-700 text-white"><ScanLine size={20} /></div><div><div className="text-xs font-semibold uppercase tracking-wide text-primary-800">Selected item</div><div className="font-semibold text-primary-950">{product?.name}</div><div className="text-sm text-primary-900">{product?.brand?.name || selectedCategory?.brands.find((item) => item.id === brandId)?.name} · {product?.category?.name || selectedCategory?.name}</div><div className="mt-1 text-sm">{selectedVariantSummary.size}{selectedVariantSummary.color ? ` · ${selectedVariantSummary.color}` : ""} · MRP ₹{variant.mrp ?? "—"} · Purchase cost ₹{variant.last_purchase_cost} · Stock: {selectedVariantSummary.stock}</div></div></div><div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]"><label className="field-label">Scan manufacturer barcode<input className="field-input mt-1 font-mono" placeholder="Scan or enter barcode" value={barcode} onChange={(event) => setBarcode(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void stage(); } }} /></label><div className="flex items-end"><Button type="button" onClick={() => void stage()} disabled={pending || !barcode.trim()}>{pending ? "Staging" : quantityMode === "INCREMENT" ? "Assign & Stage" : `Stage ${quantity || 0} pieces`}</Button></div></div><div className="mt-3 flex flex-wrap items-center gap-3"><div className="inline-flex rounded-lg border border-primary-200 bg-white p-1"><button type="button" onClick={() => setQuantityMode("INCREMENT")} className={`rounded-md px-3 py-2 text-xs font-semibold ${quantityMode === "INCREMENT" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Each scan adds 1</button><button type="button" onClick={() => setQuantityMode("QUANTITY_ENTRY")} className={`rounded-md px-3 py-2 text-xs font-semibold ${quantityMode === "QUANTITY_ENTRY" ? "bg-primary-700 text-white" : "text-slate-600"}`}>Enter quantity</button></div>{quantityMode === "QUANTITY_ENTRY" ? <label className="field-label">Quantity<input className="field-input mt-1 w-28" type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label> : null}<Button type="button" variant="secondary" onClick={() => { setVariant(null); setBarcode(""); }}>Add Another Variant</Button></div></section> : null}
    {error ? <ErrorState message={error} /> : null}
    {sharedConfirmation ? <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><h3 className="font-semibold">This manufacturer barcode is used by other items</h3><p className="mt-1">Add it to the selected exact variant without removing the other valid mappings.</p>{sharedConfirmation.targets.length ? <ul className="mt-2 list-disc pl-5 text-xs">{sharedConfirmation.targets.map((target) => <li key={target.variant_id}>{target.product_name} · {target.size || "Standard"}{target.color ? ` · ${target.color}` : ""}</li>)}</ul> : null}<div className="mt-3 flex flex-wrap gap-2"><Button type="button" onClick={() => void stage(true)}>Add to Selected Variant</Button><Button type="button" variant="secondary" onClick={() => document.getElementById("other-barcode-items")?.scrollIntoView({ behavior: "smooth" })}>View Other Items</Button><Button type="button" variant="secondary" onClick={() => setSharedConfirmation(null)}>Cancel</Button></div></section> : null}
    {conflict ? <section className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-950"><h3 className="font-semibold">Barcode belongs to another product.</h3><p className="mt-1"><strong>{conflict.product_name}</strong>{conflict.brand_name ? ` · ${conflict.brand_name}` : ""}{conflict.size ? ` · ${conflict.size}` : ""}{conflict.color ? ` · ${conflict.color}` : ""}</p></section> : null}
    <Dialog open={categoryDialog} title="Add Category" onClose={() => setCategoryDialog(false)}><label className="field-label">Category name<input autoFocus className="field-input mt-1" value={catalogName} onChange={(event) => setCatalogName(event.target.value)} /></label><div className="mt-4 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setCategoryDialog(false)}>Cancel</Button><Button type="button" disabled={pending} onClick={() => void createCategory()}>Add Category</Button></div></Dialog>
    <Dialog open={brandDialog} title="Add Brand" onClose={() => setBrandDialog(false)}><label className="field-label">Brand name<input autoFocus className="field-input mt-1" value={catalogName} onChange={(event) => setCatalogName(event.target.value)} /></label><div className="mt-4 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setBrandDialog(false)}>Cancel</Button><Button type="button" disabled={pending} onClick={() => void createBrand()}>Add Brand</Button></div></Dialog>
    <Dialog open={productDialog} title="Create Product" description="This creates the product family with zero stock." onClose={() => setProductDialog(false)}><form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => void createProduct(event)}><label className="field-label sm:col-span-2">Product/style name<input autoFocus className="field-input mt-1" value={name} onChange={(event) => setName(event.target.value)} /></label><label className="field-label">MRP<input className="field-input mt-1" type="number" min="0" value={mrp} onChange={(event) => setMrp(event.target.value)} /></label><label className="field-label">Selling price<input className="field-input mt-1" required type="number" min="0" value={sellingPrice} onChange={(event) => setSellingPrice(event.target.value)} /></label><label className="field-label">Purchase cost<input className="field-input mt-1" required type="number" min="0" value={purchaseCost} onChange={(event) => setPurchaseCost(event.target.value)} /></label><div className="sm:col-span-2 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setProductDialog(false)}>Cancel</Button><Button type="submit" disabled={pending}>Create Product</Button></div></form></Dialog>
    <Dialog open={variantDialog} title="Add Variant" description="This creates zero stock. Barcode assignment and stock staging happen separately." onClose={() => setVariantDialog(false)}><form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => void createVariant(event)}><label className="field-label">Size<input autoFocus className="field-input mt-1" list="stock-size-suggestions" placeholder="e.g. M, 32B, Free Size" value={size} onChange={(event) => setSize(event.target.value)} /><datalist id="stock-size-suggestions"><option value="S" /><option value="M" /><option value="L" /><option value="XL" /><option value="2XL" /><option value="3XL" /><option value="32B" /><option value="32C" /><option value="34B" /><option value="34C" /><option value="Free Size" /><option value="Custom Size" /></datalist></label><label className="field-label">Colour<input className="field-input mt-1" value={color} onChange={(event) => setColor(event.target.value)} /></label><label className="field-label">MRP<input className="field-input mt-1" type="number" min="0" value={mrp} onChange={(event) => setMrp(event.target.value)} /></label><label className="field-label">Selling price<input className="field-input mt-1" required type="number" min="0" value={sellingPrice} onChange={(event) => setSellingPrice(event.target.value)} /></label><label className="field-label">Purchase cost<input className="field-input mt-1" required type="number" min="0" value={purchaseCost} onChange={(event) => setPurchaseCost(event.target.value)} /></label><div className="sm:col-span-2 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setVariantDialog(false)}>Cancel</Button><Button type="submit" disabled={pending}>Add Variant</Button></div></form></Dialog>
  </section>;
}

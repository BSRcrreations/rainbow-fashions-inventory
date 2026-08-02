import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ImagePlus, PackagePlus, Plus, Search } from "lucide-react";
import { api } from "../api/client";
import type { BarcodeImageResolution, CategoryHierarchy, SaleCatalogProduct, StockScanSession } from "../types";
import Dialog from "./Dialog";
import ErrorState from "./ErrorState";
import { existingVariantBarcodePayload } from "./barcodeOnboardingLogic";
import { Button } from "./ui/button";

type OnboardingAction = "EXISTING_VARIANT" | "NEW_VARIANT" | "NEW_PRODUCT";

interface Props {
  open: boolean;
  barcode: string;
  session: StockScanSession;
  initialAction?: OnboardingAction;
  initialQuantity?: string;
  onClose: () => void;
  onSaved: (session: StockScanSession, action: OnboardingAction) => void;
}

const blank = {
  product_name: "", category_id: "", subcategory_id: "", brand_id: "", product_code: "", style_code: "", manufacturer_sku: "", internal_sku: "",
  size: "", color: "", hsn_sac: "", quantity: "1", package_quantity: "1", scan_unit: "PIECE", inventory_unit: "PIECE", sale_mode: "PIECE_ONLY",
  purchase_cost: "", mrp: "", selling_price: "", pricing_type: "OWN_PRICE", product_date: "", minimum_stock: "0", description: "", alternate_barcode: "", package_barcode: "", package_barcode_quantity: "1", image_url: "",
};

function detail(variant: { size?: string | null; color?: string | null; style_code?: string | null; sku?: string | null }) {
  return [variant.size, variant.color, variant.style_code].filter(Boolean).join(" / ") || variant.sku || "Standard";
}

export default function BarcodeOnboardingDialog({ open, barcode, session, initialAction = "NEW_PRODUCT", initialQuantity = "1", onClose, onSaved }: Props) {
  const [action, setAction] = useState<OnboardingAction>(initialAction);
  const [selectedVariantId, setSelectedVariantId] = useState("");
  const [selectedProductId, setSelectedProductId] = useState("");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(() => ({ ...blank, quantity: initialQuantity, category_id: session.default_category_id ?? "", brand_id: session.default_brand_id ?? "", purchase_cost: session.default_purchase_cost ?? "", selling_price: session.default_selling_price ?? "" }));
  const [error, setError] = useState("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newSubcategoryName, setNewSubcategoryName] = useState("");
  const [newBrandName, setNewBrandName] = useState("");
  const [imageInfo, setImageInfo] = useState<BarcodeImageResolution | null>(null);

  const hierarchyQuery = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy"), enabled: open });
  const catalogQuery = useQuery({ queryKey: ["stock-onboard-catalog", search], queryFn: () => api.get<SaleCatalogProduct[]>(`/sales/catalog${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`), enabled: open && action !== "NEW_PRODUCT" });
  const categories = hierarchyQuery.data ?? [];
  const selectedCategory = categories.find((category) => category.id === form.category_id);
  const brands = selectedCategory?.brands.filter((brand) => brand.is_active) ?? [];
  const subcategories = selectedCategory?.subcategories.filter((subcategory) => subcategory.is_active) ?? [];
  const selectedVariant = (catalogQuery.data ?? []).flatMap((product) => product.variants.map((variant) => ({ product, variant }))).find(({ variant }) => variant.variant_id === selectedVariantId);

  function update(key: keyof typeof blank, value: string) { setForm((current) => ({ ...current, [key]: value })); }
  function chooseCategory(value: string) { const category = categories.find((item) => item.id === value); setForm((current) => ({ ...current, category_id: value, brand_id: "", subcategory_id: category?.subcategories.find((item) => item.is_active)?.id ?? "" })); }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => { const body = new FormData(); body.append("file", file); return api.post<BarcodeImageResolution>("/barcodes/resolve-image", body); },
    onSuccess: (result) => {
      setImageInfo(result);
      setForm((current) => ({
        ...current,
        image_url: result.image_url,
        product_name: current.product_name || result.suggestions.product_name?.value || "",
        product_code: current.product_code || result.suggestions.product_code?.value || "",
        style_code: current.style_code || result.suggestions.style_code?.value || "",
        size: current.size || result.suggestions.size?.value || "",
        color: current.color || result.suggestions.color?.value || "",
        hsn_sac: current.hsn_sac || result.suggestions.hsn_sac?.value || "",
        mrp: current.mrp || result.suggestions.mrp?.value || "",
        package_quantity: current.package_quantity === "1" ? result.suggestions.package_quantity?.value || "1" : current.package_quantity,
      }));
    },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to read the label image"),
  });
  const createCategoryMutation = useMutation({
    mutationFn: async () => {
      const category = await api.post<{ id: string }>("/categories", { name: newCategoryName });
      const subcategory = await api.post<{ id: string }>("/subcategories", { category_id: category.id, name: "General" });
      return { category, subcategory };
    },
    onSuccess: ({ category, subcategory }) => { setForm((current) => ({ ...current, category_id: category.id, subcategory_id: subcategory.id, brand_id: "" })); setNewCategoryName(""); void hierarchyQuery.refetch(); },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to create category"),
  });
  const createBrandMutation = useMutation({
    mutationFn: () => api.post<{ id: string }>("/brands", { category_id: form.category_id, name: newBrandName }),
    onSuccess: (brand) => { update("brand_id", brand.id); setNewBrandName(""); void hierarchyQuery.refetch(); },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to create brand"),
  });
  const createSubcategoryMutation = useMutation({
    mutationFn: () => api.post<{ id: string }>("/subcategories", { category_id: form.category_id, name: newSubcategoryName }),
    onSuccess: (subcategory) => { update("subcategory_id", subcategory.id); setNewSubcategoryName(""); void hierarchyQuery.refetch(); },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to create subcategory"),
  });
  const onboardMutation = useMutation({
    mutationFn: () => {
      if (action === "EXISTING_VARIANT" && !selectedVariantId) throw new Error("Select the exact existing variant");
      if (action === "NEW_VARIANT" && !selectedProductId) throw new Error("Select the product for the new variant");
      if (action === "NEW_PRODUCT" && (!form.product_name.trim() || !form.category_id || !form.brand_id)) throw new Error("Enter a product name, category, and brand");
      if (action !== "EXISTING_VARIANT") {
        if (!Number.isFinite(Number(form.purchase_cost)) || Number(form.purchase_cost) < 0) throw new Error("Enter the purchase cost for this stock receipt");
        if (!Number.isFinite(Number(form.selling_price)) || Number(form.selling_price) < 0) throw new Error("Enter the normal selling price");
        if (form.pricing_type === "MRP" && !form.mrp) throw new Error("Enter MRP when using MRP pricing");
        if (form.mrp && Number(form.selling_price) > Number(form.mrp)) throw new Error("Selling price cannot be greater than MRP");
        if (Number(form.package_quantity) > 1 && form.scan_unit !== "PACK") throw new Error("Package quantities above one must use Pack as the scan unit");
      }
      if (action === "EXISTING_VARIANT") {
        return api.post<StockScanSession>("/barcodes/onboard-product", existingVariantBarcodePayload(session.id, barcode, selectedVariantId, Number(form.quantity)));
      }
      return api.post<StockScanSession>("/barcodes/onboard-product", {
        session_id: session.id, action, barcode,
        existing_product_id: action === "NEW_VARIANT" ? selectedProductId : undefined,
        ...form, quantity: Number(form.quantity), package_quantity: Number(form.package_quantity), package_barcode_quantity: Number(form.package_barcode_quantity), minimum_stock: Number(form.minimum_stock), product_date: form.product_date || null, purchase_cost: Number(form.purchase_cost), mrp: form.mrp ? Number(form.mrp) : null, selling_price: Number(form.selling_price),
      });
    },
    onSuccess: (next) => { onSaved(next, action); onClose(); },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Unable to save this barcode mapping"),
  });

  const showVariantFields = action !== "EXISTING_VARIANT";
  return <Dialog open={open} onClose={onClose} title="Barcode not registered" description="Create or select the exact sellable product without leaving this stock draft." maxWidth="xl">
    <label className="field-label">Scanned barcode<input className="field-input" value={barcode} readOnly /></label>
    <div className="flex flex-wrap gap-2 border-b border-border pb-4">{(["EXISTING_VARIANT", "NEW_VARIANT", "NEW_PRODUCT"] as OnboardingAction[]).map((value) => <button key={value} type="button" onClick={() => setAction(value)} className={`rounded-lg px-3 py-2 text-sm font-semibold ${action === value ? "bg-primary-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{value === "EXISTING_VARIANT" ? "Assign existing variant" : value === "NEW_VARIANT" ? "Create new variant" : "Create new product"}</button>)}</div>
    {error ? <div className="mt-4"><ErrorState message={error} /></div> : null}
    <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_260px]">
      <div className="space-y-4">
        {action !== "NEW_PRODUCT" ? <section><label className="field-label">{action === "EXISTING_VARIANT" ? "Search existing products and variants" : "Find existing product or variant"}<div className="relative mt-1"><Search size={16} className="absolute left-3 top-3 text-muted" /><input className="field-input pl-9" placeholder="Search product, SKU, barcode, style, brand, size, or colour" value={search} onChange={(event) => setSearch(event.target.value)} /></div></label><div className="mt-2 max-h-52 space-y-2 overflow-y-auto">{(catalogQuery.data ?? []).map((product) => <div key={product.product_id} className={`rounded-lg border p-3 ${selectedProductId === product.product_id ? "border-primary-400 bg-primary-50" : "border-border"}`}><button type="button" className="w-full text-left" onClick={() => { setSelectedProductId(product.product_id); if (action === "NEW_VARIANT") setAction("NEW_VARIANT"); }}><div className="font-semibold">{product.name}</div><div className="text-xs text-muted">{product.category_name} · {product.brand_name}</div></button>{action === "EXISTING_VARIANT" ? <div className="mt-2 grid gap-1 sm:grid-cols-2">{product.variants.map((variant) => <button key={variant.variant_id} type="button" onClick={() => setSelectedVariantId(variant.variant_id)} className={`rounded-md border px-2 py-2 text-left text-xs ${selectedVariantId === variant.variant_id ? "border-primary-500 bg-primary-100" : "border-border hover:bg-slate-50"}`}><div className="font-semibold">{detail(variant)}</div><div>{variant.sku} · {variant.available_stock} available</div></button>)}</div> : null}</div>)}</div></section> : null}
        {action === "NEW_PRODUCT" ? <section className="grid gap-3 sm:grid-cols-2">
          <label className="field-label sm:col-span-2">Product name<input className="field-input" value={form.product_name} onChange={(event) => update("product_name", event.target.value)} /></label>
          <label className="field-label">Category<select className="field-input" value={form.category_id} onChange={(event) => chooseCategory(event.target.value)}><option value="">Select category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <label className="field-label">Subcategory<select className="field-input" value={form.subcategory_id} onChange={(event) => update("subcategory_id", event.target.value)}><option value="">Select subcategory</option>{subcategories.map((subcategory) => <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>)}</select></label>
          <div className="sm:col-span-2 flex flex-wrap items-end gap-2"><label className="field-label flex-1">+ New Category<input className="field-input" placeholder="Category name" value={newCategoryName} onChange={(event) => setNewCategoryName(event.target.value)} /></label><Button type="button" variant="secondary" disabled={!newCategoryName.trim() || createCategoryMutation.isPending} onClick={() => createCategoryMutation.mutate()}><Plus size={16} /> Add</Button></div>
          <div className="sm:col-span-2 flex flex-wrap items-end gap-2"><label className="field-label flex-1">+ New Subcategory<input className="field-input" disabled={!form.category_id} placeholder="Subcategory name" value={newSubcategoryName} onChange={(event) => setNewSubcategoryName(event.target.value)} /></label><Button type="button" variant="secondary" disabled={!form.category_id || !newSubcategoryName.trim() || createSubcategoryMutation.isPending} onClick={() => createSubcategoryMutation.mutate()}><Plus size={16} /> Add</Button></div>
          <label className="field-label">Brand<select className="field-input" disabled={!form.category_id} value={form.brand_id} onChange={(event) => update("brand_id", event.target.value)}><option value="">Select brand</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label>
          <div className="flex items-end gap-2"><label className="field-label flex-1">+ New Brand<input className="field-input" disabled={!form.category_id} placeholder="Brand or Unbranded" value={newBrandName} onChange={(event) => setNewBrandName(event.target.value)} /></label><Button type="button" variant="secondary" disabled={!form.category_id || !newBrandName.trim() || createBrandMutation.isPending} onClick={() => createBrandMutation.mutate()}><Plus size={16} /> Add</Button></div>
        </section> : null}
        {showVariantFields ? <section className="grid gap-3 sm:grid-cols-3"><label className="field-label">Size<input className="field-input" value={form.size} onChange={(event) => update("size", event.target.value)} /></label><label className="field-label">Colour<input className="field-input" value={form.color} onChange={(event) => update("color", event.target.value)} /></label><label className="field-label">Style / model<input className="field-input" value={form.style_code} onChange={(event) => update("style_code", event.target.value)} /></label><label className="field-label">Manufacturer SKU<input className="field-input" value={form.manufacturer_sku} onChange={(event) => update("manufacturer_sku", event.target.value)} /></label><label className="field-label">Internal SKU<input className="field-input" value={form.internal_sku} onChange={(event) => update("internal_sku", event.target.value)} /></label><label className="field-label">HSN / SAC<input className="field-input" value={form.hsn_sac} onChange={(event) => update("hsn_sac", event.target.value)} /></label></section> : null}
        {action === "EXISTING_VARIANT" ? <section className="space-y-3 rounded-xl border border-primary-200 bg-primary-50/50 p-4"><p className="text-sm text-primary-950">This assigns the scanned barcode to an existing variant only. Product details and prices will not be changed.</p>{selectedVariant ? <div className="rounded-lg border border-primary-200 bg-white p-3 text-sm"><div className="font-semibold">{selectedVariant.product.name}</div><div className="mt-1 text-muted">{selectedVariant.product.brand_name || "Unbranded"} · {detail(selectedVariant.variant)} · {selectedVariant.variant.sku}</div></div> : <p className="text-sm text-muted">Select the exact size and colour above.</p>}{session.quantity_mode === "QUANTITY_ENTRY" ? <label className="field-label max-w-xs">Quantity to add<input className="field-input" min="1" type="number" value={form.quantity} onChange={(event) => update("quantity", event.target.value)} /></label> : null}</section> : <section className="grid gap-3 sm:grid-cols-3">
          <label className="field-label">Quantity to add<input className="field-input" min="1" type="number" value={form.quantity} onChange={(event) => update("quantity", event.target.value)} /></label>
          <label className="field-label">Product date<input className="field-input" type="date" value={form.product_date} onChange={(event) => update("product_date", event.target.value)} /></label>
          <label className="field-label">Minimum stock<input className="field-input" min="0" type="number" value={form.minimum_stock} onChange={(event) => update("minimum_stock", event.target.value)} /></label>
          <label className="field-label">Purchase cost<input className="field-input" min="0" step="0.01" type="number" value={form.purchase_cost} onChange={(event) => update("purchase_cost", event.target.value)} /></label>
          <label className="field-label">Pricing type<select className="field-input" value={form.pricing_type} onChange={(event) => update("pricing_type", event.target.value)}><option value="OWN_PRICE">Own price</option><option value="MRP">MRP</option></select></label>
          <label className="field-label">MRP <span className="text-muted">optional</span><input className="field-input" min="0" step="0.01" type="number" value={form.mrp} onChange={(event) => update("mrp", event.target.value)} /></label>
          <label className="field-label">Selling price<input className="field-input" min="0" step="0.01" type="number" value={form.selling_price} onChange={(event) => update("selling_price", event.target.value)} /></label>
          <label className="field-label">Pieces per scan<input className="field-input" min="1" type="number" value={form.package_quantity} onChange={(event) => update("package_quantity", event.target.value)} /></label>
          <label className="field-label">Scan unit<select className="field-input" value={form.scan_unit} onChange={(event) => update("scan_unit", event.target.value)}><option value="PIECE">Piece</option><option value="PACK">Pack</option></select></label>
          <label className="field-label">Alternate barcode<input className="field-input" value={form.alternate_barcode} onChange={(event) => update("alternate_barcode", event.target.value)} /></label>
          <label className="field-label">Package barcode<input className="field-input" value={form.package_barcode} onChange={(event) => update("package_barcode", event.target.value)} /></label>
          <label className="field-label">Package barcode qty<input className="field-input" min="1" type="number" value={form.package_barcode_quantity} onChange={(event) => update("package_barcode_quantity", event.target.value)} /></label>
          <label className="field-label sm:col-span-3">Notes<input className="field-input" value={form.description} onChange={(event) => update("description", event.target.value)} /></label>
          <label className="field-label sm:col-span-2">How is it sold?<select className="field-input" value={form.sale_mode} onChange={(event) => update("sale_mode", event.target.value)}><option value="PIECE_ONLY">Individual pieces only</option><option value="PACK_ONLY">Complete pack only</option><option value="BOTH">Both pack and individual pieces</option></select></label>
        </section>}
      </div>
        {action !== "EXISTING_VARIANT" ? <aside className="space-y-3 rounded-xl border border-border bg-slate-50 p-4"><div><div className="text-sm font-semibold">Label photo</div><p className="mt-1 text-xs text-muted">OCR suggestions are optional and always require review.</p></div><label className="flex min-h-28 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white p-3 text-center text-sm text-slate-600 hover:border-primary-400"><ImagePlus size={20} />{uploadMutation.isPending ? "Reading label..." : "Upload or take label photo"}<input className="sr-only" accept="image/jpeg,image/png,image/webp" capture="environment" type="file" onChange={(event) => { const file = event.target.files?.[0]; if (file) uploadMutation.mutate(file); }} /></label>{imageInfo ? <><img className="h-28 w-full rounded-lg border border-border object-contain bg-white" src={imageInfo.image_url} alt="Uploaded product label" /><div className="space-y-2">{Object.entries(imageInfo.suggestions).map(([key, item]) => <div key={key} className={`rounded-md p-2 text-xs ${item.confidence < 0.8 ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}><div className="font-semibold capitalize">{key.replace(/_/g, " ")}</div><div>{item.value} · {Math.round(item.confidence * 100)}%</div></div>)}</div></> : null}<div className="rounded-lg border border-primary-100 bg-primary-50 p-3 text-xs text-primary-900"><strong>Conversion:</strong> {form.quantity || "0"} scans × {form.package_quantity || "0"} {form.scan_unit === "PACK" ? "pieces per pack" : "piece"} = {Number(form.quantity || 0) * Number(form.package_quantity || 0)} base pieces.</div></aside> : null}
    </div>
    <div className="sticky bottom-[-1.25rem] z-10 -mx-4 mt-6 flex flex-col-reverse gap-2 border-t border-border bg-surface/95 px-4 py-3 shadow-[0_-8px_16px_-16px_rgb(15_23_42/0.45)] backdrop-blur sm:-mx-6 sm:flex-row sm:justify-end sm:px-6"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="button" disabled={onboardMutation.isPending || (action === "EXISTING_VARIANT" && !selectedVariantId)} onClick={() => onboardMutation.mutate()}>{onboardMutation.isPending ? "Saving" : <><PackagePlus size={17} /> {action === "EXISTING_VARIANT" ? "Assign barcode" : action === "NEW_PRODUCT" ? "Create product and add to stock draft" : "Save and add to stock draft"}</>}</Button></div>
  </Dialog>;
}

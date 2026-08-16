import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../api/client";
import type { CategoryHierarchy, PaginatedProducts, ProductVariant } from "../types";
import Dialog from "./Dialog";
import { Button } from "./ui/button";

interface Props { open: boolean; barcode: string; onClose: () => void; onCreated: (productId: string, variantId: string) => void; }

export default function ProductBarcodeDetailsDialog({ open, barcode, onClose, onCreated }: Props) {
  const [mode, setMode] = useState<"EXISTING" | "NEW">("EXISTING");
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [productName, setProductName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [subcategoryId, setSubcategoryId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [description, setDescription] = useState("");
  const [size, setSize] = useState(""); const [color, setColor] = useState(""); const [styleCode, setStyleCode] = useState(""); const [manufacturerSku, setManufacturerSku] = useState("");
  const [sku, setSku] = useState(""); const [mrp, setMrp] = useState(""); const [sellingPrice, setSellingPrice] = useState(""); const [purchaseCost, setPurchaseCost] = useState("");
  const [scanUnit, setScanUnit] = useState<"PIECE" | "PACK">("PIECE"); const [piecesPerPack, setPiecesPerPack] = useState("1");
  const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  const hierarchyQuery = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy"), enabled: open });
  const productsQuery = useQuery({ queryKey: ["barcode-detail-products", search], queryFn: () => api.get<PaginatedProducts>(`/products?paginated=true&page=1&page_size=25${search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ""}`), enabled: open && mode === "EXISTING" });
  const categories = useMemo(() => hierarchyQuery.data ?? [], [hierarchyQuery.data]);
  const category = useMemo(() => categories.find((item) => item.id === categoryId), [categories, categoryId]);
  const selectedProduct = productsQuery.data?.items.find((item) => item.id === productId);

  function selectProduct(id: string) {
    setProductId(id);
    const product = productsQuery.data?.items.find((item) => item.id === id);
    if (product && !sellingPrice) setSellingPrice(product.selling_price);
    if (product && !purchaseCost) setPurchaseCost(product.purchase_price);
    if (product && !mrp && product.mrp) setMrp(product.mrp);
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (scanUnit === "PACK" && (!Number.isInteger(Number(piecesPerPack)) || Number(piecesPerPack) < 2)) { setError("Pieces per Pack must be a whole number of at least 2."); return; }
    setSaving(true);
    try {
      const variant = await api.post<ProductVariant>("/product-variants/details", {
        product_id: mode === "EXISTING" ? productId : null, product_name: mode === "NEW" ? productName : null,
        category_id: mode === "NEW" ? categoryId : null, subcategory_id: mode === "NEW" ? subcategoryId : null, brand_id: mode === "NEW" ? brandId : null, description: mode === "NEW" ? description || null : null,
        barcode, internal_sku: sku, size: size || null, color: color || null, style_code: styleCode || null, manufacturer_sku: manufacturerSku || null,
        mrp: mrp || null, selling_price: sellingPrice, purchase_cost: purchaseCost, scan_unit: scanUnit, pieces_per_pack: scanUnit === "PACK" ? Number(piecesPerPack) : 1,
      });
      onCreated(variant.product_id, variant.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to add details"); }
    finally { setSaving(false); }
  }
  return <Dialog open={open} title="NEW VARIANT / BARCODE DETAILS" description="The scan only loaded this barcode. Review every value; nothing is created or mapped until Add Details." onClose={onClose} maxWidth="xl">
    <form className="space-y-5" onSubmit={submit}>
      <label className="field-label">Scanned barcode<input className="field-input mt-1 font-mono" readOnly value={barcode} /></label>
      <div className="flex flex-wrap gap-2"><Button type="button" variant={mode === "EXISTING" ? "default" : "secondary"} onClick={() => setMode("EXISTING")}>Existing product</Button><Button type="button" variant={mode === "NEW" ? "default" : "secondary"} onClick={() => setMode("NEW")}>New product</Button></div>
      {mode === "EXISTING" ? <section className="rounded-lg border border-line p-4"><label className="field-label">Select product<div className="field-input mt-1 flex items-center gap-2"><Search size={16} className="text-slate-400" /><input className="min-w-0 flex-1 border-0 bg-transparent outline-none" placeholder="Search product, SKU, barcode, brand" value={search} onChange={(event) => setSearch(event.target.value)} /></div></label><select required className="field-input mt-3" value={productId} onChange={(event) => selectProduct(event.target.value)}><option value="">Select product</option>{(productsQuery.data?.items ?? []).map((product) => <option key={product.id} value={product.id}>{product.name} · {product.brand?.name || "Unbranded"} · {product.category?.name || ""}</option>)}</select>{selectedProduct ? <p className="mt-2 text-sm text-slate-600">Variant will be added to <strong>{selectedProduct.name}</strong>. Parent product details are unchanged.</p> : null}</section> : <section className="grid gap-3 rounded-lg border border-line p-4 sm:grid-cols-2"><label className="field-label sm:col-span-2">Product name<input required className="field-input mt-1" value={productName} onChange={(event) => setProductName(event.target.value)} /></label><label className="field-label">Category<select required className="field-input mt-1" value={categoryId} onChange={(event) => { setCategoryId(event.target.value); setSubcategoryId(""); setBrandId(""); }}><option value="">Select category</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field-label">Subcategory<select required className="field-input mt-1" value={subcategoryId} onChange={(event) => setSubcategoryId(event.target.value)}><option value="">Select subcategory</option>{(category?.subcategories ?? []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field-label">Brand<select required className="field-input mt-1" value={brandId} onChange={(event) => setBrandId(event.target.value)}><option value="">Select brand</option>{(category?.brands ?? []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field-label">Description<input className="field-input mt-1" value={description} onChange={(event) => setDescription(event.target.value)} /></label></section>}
      <section className="grid gap-3 sm:grid-cols-3"><label className="field-label">Size<input className="field-input mt-1" value={size} onChange={(event) => setSize(event.target.value)} /></label><label className="field-label">Colour<input className="field-input mt-1" value={color} onChange={(event) => setColor(event.target.value)} /></label><label className="field-label">Style / model<input className="field-input mt-1" value={styleCode} onChange={(event) => setStyleCode(event.target.value)} /></label><label className="field-label">SKU<input required className="field-input mt-1" value={sku} onChange={(event) => setSku(event.target.value)} /></label><label className="field-label">Manufacturer SKU<input className="field-input mt-1" value={manufacturerSku} onChange={(event) => setManufacturerSku(event.target.value)} /></label><label className="field-label">MRP<input className="field-input mt-1" type="number" min="0" step="0.01" value={mrp} onChange={(event) => setMrp(event.target.value)} /></label><label className="field-label">Selling price<input required className="field-input mt-1" type="number" min="0" step="0.01" value={sellingPrice} onChange={(event) => setSellingPrice(event.target.value)} /></label><label className="field-label">Purchase cost<input required className="field-input mt-1" type="number" min="0" step="0.01" value={purchaseCost} onChange={(event) => setPurchaseCost(event.target.value)} /></label><label className="field-label">Scan method<select className="field-input mt-1" value={scanUnit} onChange={(event) => setScanUnit(event.target.value as "PIECE" | "PACK")}><option value="PIECE">Piece</option><option value="PACK">Pack</option></select></label>{scanUnit === "PACK" ? <label className="field-label">Pieces per pack<input required className="field-input mt-1" type="number" min="2" step="1" value={piecesPerPack} onChange={(event) => setPiecesPerPack(event.target.value)} /></label> : <p className="self-end text-sm text-slate-500">Piece scan = 1 inventory piece.</p>}</section>
      {error ? <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
      <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? "Saving" : "Add Details"}</Button></div>
    </form>
  </Dialog>;
}

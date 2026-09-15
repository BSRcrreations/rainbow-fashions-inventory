import { resolveSharedVariant } from "../utils/variantSelection";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../api/client";
import type { CategoryHierarchy, ProductVariantBarcode, SaleCatalogProduct, SaleCatalogVariant } from "../types";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { catalogItemFromBarcode } from "../pages/newSaleLogic";
import { orderVariantsBySize } from "../pages/newSaleCard";
import { money } from "../utils/format";
import BarcodeScannerInput from "./BarcodeScannerInput";
import Dialog from "./Dialog";
import ErrorState from "./ErrorState";
import { Button } from "./ui/button";

export type CatalogPage = { items: SaleCatalogProduct[]; total: number; page: number; page_size: number };
export type SharedTarget = { variant_id: string; product_id: string; product_name: string; brand_name?: string | null; size?: string | null; color?: string | null; current_stock: number };

export function CategoryButtons({ categories, selected, onSelect }: { categories: Array<{ id: string; name: string }>; selected: string; onSelect: (id: string) => void }) {
  return <nav aria-label="Product categories" className="flex max-h-52 flex-wrap gap-2 overflow-y-auto rounded-xl border bg-white p-3"><button type="button" aria-pressed={!selected} className={`focus-ring min-h-12 rounded-xl border px-5 font-bold ${!selected ? "bg-primary-700 text-white" : "bg-slate-50 text-slate-800"}`} onClick={() => onSelect("")}>All categories</button>{categories.map((category) => <button key={category.id} type="button" aria-pressed={selected === category.id} className={`focus-ring min-h-12 rounded-xl border px-5 text-base font-bold ${selected === category.id ? "bg-primary-700 text-white" : "bg-slate-50 text-slate-800 hover:bg-primary-50"}`} onClick={() => onSelect(category.id)}>{category.name}</button>)}</nav>;
}


export default function VariantPicker({ onSelect, requireStock = false }: { onSelect: (product: SaleCatalogProduct, variant: SaleCatalogVariant) => void; requireStock?: boolean }) {
  const [search, setSearch] = useState(""); const [category, setCategory] = useState(""); const [page, setPage] = useState(1);
  const [shared, setShared] = useState<SharedTarget[]>([]); const [error, setError] = useState("");
  const debounced = useDebouncedValue(search, 250);
  const hierarchy = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy") });
  const query = useQuery({ queryKey: ["pos-variant-catalog", debounced, category, page], queryFn: () => api.get<CatalogPage>(`/sales/catalog?paginated=true&page=${page}&page_size=24&search=${encodeURIComponent(debounced)}${category ? `${category ? `&category_id=${category}` : ""}` : ""}`) });
  function choose(product: SaleCatalogProduct, variant: SaleCatalogVariant) { if (requireStock && variant.available_stock < 1) { setError("This size is out of stock."); return; } setError(""); onSelect(product, variant); }
  async function scan(barcode: string, signal: AbortSignal) {
    const targets = await api.get<SharedTarget[]>(`/barcodes/${encodeURIComponent(barcode)}/shared-targets`, { signal });
    if (targets.length > 1) { setShared(targets); return; }
    const found = await api.get<ProductVariantBarcode>(`/product-variants/by-barcode/${encodeURIComponent(barcode)}`, { signal });
    const resolved = catalogItemFromBarcode(found); choose(resolved.product, resolved.variant);
  }
  async function selectShared(target: SharedTarget) { try { const resolved = await resolveSharedVariant(target); choose(resolved.product, resolved.variant); setShared([]); } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load this size."); } }
  const products = query.data?.items ?? [];
  return <div className="space-y-4"><BarcodeScannerInput label="Scan or type barcode" placeholder="Barcode is optional" onScan={scan} /><label className="field-label"><span className="flex items-center gap-2 text-slate-800"><Search size={18} />Search product, brand, size or colour</span><input className="field-input" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Type a name, or choose a category below" /></label><CategoryButtons categories={(hierarchy.data ?? []).filter((item) => item.is_active)} selected={category} onSelect={(id) => { setCategory(id); setPage(1); }} />{error || query.error ? <ErrorState message={error || (query.error instanceof Error ? query.error.message : "Unable to load products.")} /> : null}{query.isLoading ? <p role="status">Loading products…</p> : null}<div className="grid gap-3 sm:grid-cols-2">{products.map((product) => <article key={product.product_id} className="rounded-xl border bg-white p-4"><h3 className="text-lg font-bold">{product.name}</h3><p className="mt-1 text-sm text-slate-700">{product.brand_name || "Unbranded"} · {product.category_name}</p><div className="mt-3 flex flex-wrap gap-2">{orderVariantsBySize(product.variants).map((variant) => <button key={variant.variant_id} type="button" disabled={!variant.is_active || (requireStock && variant.available_stock < 1)} onClick={() => choose(product, variant)} className="focus-ring min-h-14 rounded-lg border border-primary-200 bg-primary-50 px-4 py-2 text-left text-primary-950 disabled:opacity-50"><strong className="block">{variant.size || "Standard"}{variant.color ? ` · ${variant.color}` : ""}</strong><span className="text-sm">{money(variant.selling_price)} · {variant.available_stock > 0 ? `${variant.available_stock} in stock` : "Out of stock"}</span></button>)}</div></article>)}</div>{!query.isLoading && !products.length ? <p className="rounded-xl border bg-white p-5">No products found. Try another name or category.</p> : null}<div className="flex items-center justify-between gap-3"><Button type="button" variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm">Page {page} · {query.data?.total ?? 0} products</span><Button type="button" variant="secondary" disabled={page * 24 >= (query.data?.total ?? 0)} onClick={() => setPage(page + 1)}>Next</Button></div><Dialog open={shared.length > 0} title="Choose the exact size" description="This barcode is shared. Select the item in your hand." onClose={() => setShared([])}><div className="grid gap-3">{shared.map((target) => <Button key={target.variant_id} type="button" variant="secondary" className="h-auto min-h-16 justify-start p-4 text-left" disabled={requireStock && target.current_stock < 1} onClick={() => void selectShared(target)}><span><strong className="block text-xl">{target.size || "Standard"}{target.color ? ` · ${target.color}` : ""}</strong>{target.product_name} · {target.current_stock} in stock</span></Button>)}</div></Dialog></div>;
}

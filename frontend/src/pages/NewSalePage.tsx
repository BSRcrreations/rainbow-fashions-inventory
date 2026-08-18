import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Banknote, CheckCircle2, CreditCard, FileText, Minus, PackageOpen, Plus, Printer, ReceiptText, Search, ShoppingBag, ShoppingCart, Smartphone, Trash2, WalletCards, X } from "lucide-react";
import { api } from "../api/client";
import BarcodeScannerInput from "../components/BarcodeScannerInput";
import ConfirmDialog from "../components/ConfirmDialog";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import type { ProductVariantBarcode, Sale, SaleCatalogProduct, SaleCatalogVariant } from "../types";
import { money } from "../utils/format";
import { categoryBrandLine, orderVariantsBySize, productCardMrpText, productCardVariantSummary } from "./newSaleCard";
import { catalogItemFromBarcode, firstSellableProduct, mergeCartVariant, productForVariant } from "./newSaleLogic";
import type { CartLine } from "./newSaleLogic";
import { previewSaleDiscount, saleDiscountLabel } from "./saleDiscount";
import type { SaleDiscountPreview, SaleDiscountType } from "./saleDiscount";

type PaymentMode = "CASH" | "UPI" | "CARD" | "BANK" | "OTHER";
type StockFilter = "ALL" | "IN_STOCK" | "LOW_STOCK" | "OUT_OF_STOCK";

const paymentOptions: Array<{ value: PaymentMode; label: string; icon: typeof Banknote }> = [
  { value: "CASH", label: "Cash", icon: Banknote }, { value: "UPI", label: "UPI", icon: Smartphone },
  { value: "CARD", label: "Card", icon: CreditCard }, { value: "BANK", label: "Bank", icon: WalletCards },
];

const brandBadgeTones = ["bg-teal-50 text-teal-800 ring-teal-200", "bg-sky-50 text-sky-800 ring-sky-200", "bg-violet-50 text-violet-800 ring-violet-200", "bg-amber-50 text-amber-800 ring-amber-200", "bg-rose-50 text-rose-800 ring-rose-200"];

function variantLabel(variant: SaleCatalogVariant) { return [variant.size, variant.color, variant.style_code].filter(Boolean).join(" · ") || variant.sku; }
function brandBadgeTone(brandName?: string | null) { return brandBadgeTones[(brandName || "").split("").reduce((total, character) => total + character.charCodeAt(0), 0) % brandBadgeTones.length]; }
function uniqueValues(values: Array<string | null | undefined>) { return [...new Set(values.filter((value): value is string => Boolean(value?.trim())).map((value) => value.trim()))]; }
function stockState(product: SaleCatalogProduct): StockFilter { if (product.total_stock <= 0) return "OUT_OF_STOCK"; return product.minimum_stock > 0 && product.total_stock < product.minimum_stock ? "LOW_STOCK" : "IN_STOCK"; }

function groupCatalog(products: SaleCatalogProduct[]) {
  const groups = new Map<string, SaleCatalogProduct>();
  for (const product of products) {
    const key = [product.name.trim().toLowerCase(), product.brand_name?.trim().toLowerCase(), product.category_name?.trim().toLowerCase()].join("|");
    const existing = groups.get(key);
    if (!existing) { groups.set(key, { ...product, variants: [...product.variants], variant_count: product.variants.length, total_stock: product.total_stock ?? product.total_available_stock, total_available_stock: product.total_available_stock }); continue; }
    existing.variants.push(...product.variants);
    existing.variant_count = existing.variants.length;
    existing.total_stock += product.total_stock ?? product.total_available_stock;
    existing.total_available_stock += product.total_available_stock;
    existing.minimum_stock += product.minimum_stock;
    if (!existing.brand_logo_url) existing.brand_logo_url = product.brand_logo_url;
    if (!existing.product_image_url) existing.product_image_url = product.product_image_url;
  }
  return [...groups.values()];
}

export function ProductVisual({ product, compact = false }: { product: SaleCatalogProduct; compact?: boolean }) {
  const [failedUrls, setFailedUrls] = useState<string[]>([]);
  const imageCandidates = [product.brand_logo_url, ...(compact ? [] : [product.product_image_url])].flatMap((url) => url && !failedUrls.includes(url) ? [url] : []);
  const imageUrl = imageCandidates[0];
  const isBrandLogo = imageUrl === product.brand_logo_url;
  const initials = (product.brand_name || product.name).split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
  const dimensions = compact ? "h-10 w-10 rounded-lg text-sm" : "h-16 w-16 rounded-2xl text-lg";
  if (imageUrl) return <img loading="lazy" src={imageUrl} alt={isBrandLogo ? `${product.brand_name || product.name} logo` : product.name} className={`${dimensions} shrink-0 border border-slate-100 bg-slate-50 p-1 ${isBrandLogo ? "object-contain" : "object-cover"}`} onError={() => setFailedUrls((current) => [...current, imageUrl])} />;
  if (initials) return <div className={`grid shrink-0 place-items-center bg-gradient-to-br from-teal-50 to-cyan-100 font-extrabold text-teal-800 ring-1 ring-teal-100 ${dimensions}`}>{initials}</div>;
  return <div className={`grid shrink-0 place-items-center bg-slate-100 text-slate-400 ${dimensions}`}><PackageOpen size={compact ? 18 : 26} /></div>;
}

export function ProductGroupCard({ product, selected, onChoose, onSelectVariant }: { product: SaleCatalogProduct; selected: boolean; onChoose: () => void; onSelectVariant?: (variant: SaleCatalogVariant) => void }) {
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const state = stockState(product);
  const stockText = state === "OUT_OF_STOCK" ? "Out of stock" : state === "LOW_STOCK" ? `Low stock: ${product.total_stock}` : `${product.total_stock} in stock`;
  const stockColor = state === "OUT_OF_STOCK" ? "text-rose-700" : state === "LOW_STOCK" ? "text-amber-700" : "text-emerald-700";
  const categoryBrand = categoryBrandLine(product.category_name, product.brand_name);
  const variants = orderVariantsBySize(product.variants);
  const hasSizeChoices = variants.some((variant) => Boolean(variant.size?.trim()));
  const selectedVariant = variants.find((variant) => variant.variant_id === selectedVariantId) ?? null;
  const variantSummary = productCardVariantSummary(product);
  const mrpText = selectedVariant ? `MRP ${selectedVariant.mrp ? money(selectedVariant.mrp) : "-"}` : productCardMrpText(product);
  function chooseVariant(variant: SaleCatalogVariant) {
    setSelectedVariantId(variant.variant_id);
    onSelectVariant?.(variant);
  }
  return <article className={`group flex min-h-[156px] w-full items-start gap-3 rounded-xl border p-4 text-left shadow-sm transition duration-200 ${selected ? "border-teal-600 bg-teal-50/50 shadow-md" : "border-slate-200 bg-white hover:border-teal-400 hover:shadow-md"}`}>
    <ProductVisual product={product} compact />
    <div className="flex min-w-0 flex-1 flex-col self-stretch"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><button type="button" aria-pressed={selected} onClick={onChoose} className="text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"><h3 className="max-h-10 overflow-hidden break-normal text-base font-extrabold leading-5 tracking-tight text-slate-950 [hyphens:none] [overflow-wrap:normal]">{product.name}</h3></button></div>{product.brand_name ? <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-bold ring-1 ring-inset ${brandBadgeTone(product.brand_name)}`}>{product.brand_name}</span> : null}</div>
      <p className="mt-1.5 truncate text-sm text-slate-500">{categoryBrand}</p>
      {hasSizeChoices ? <div className="mt-3" data-testid={`size-chips-${product.product_id}`}><div className="text-xs font-bold uppercase tracking-wide text-slate-500">{selectedVariant?.size ? `Size: ${selectedVariant.size}` : "Select size"}</div><div className="mt-1.5 flex flex-wrap gap-1.5">{variants.map((variant) => { const unavailable = !variant.is_active || variant.available_stock <= 0; const isSelected = selectedVariant?.variant_id === variant.variant_id; const label = variant.size?.trim() || "Standard"; return <button key={variant.variant_id} type="button" disabled={unavailable} aria-pressed={isSelected} aria-label={`Select ${label}${variant.color ? `, ${variant.color}` : ""}`} title={unavailable ? `${label} is out of stock` : `${label}: ${variant.available_stock} in stock`} onClick={() => chooseVariant(variant)} className={`min-h-9 rounded-lg border px-2.5 text-sm font-bold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${isSelected ? "border-teal-700 bg-teal-700 text-white" : unavailable ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400 line-through" : "border-teal-200 bg-teal-50 text-teal-800 hover:border-teal-500 hover:bg-teal-100"}`}>{label}</button>; })}</div></div> : variantSummary ? <p className="mt-1 truncate text-sm font-semibold text-slate-700">{variantSummary}</p> : null}
      <p className="mt-2 truncate text-sm font-bold text-slate-900">{mrpText}</p>
      {selectedVariant ? <p className="mt-1 text-xs font-semibold text-slate-600">{selectedVariant.color ? `Colour: ${selectedVariant.color} · ` : ""}{money(selectedVariant.selling_price)} · {selectedVariant.available_stock} in stock</p> : null}
      <div className="mt-auto flex items-end justify-between gap-3 pt-3"><span className="text-sm font-bold text-teal-800">{product.variant_count} variant{product.variant_count === 1 ? "" : "s"}</span><span className={`text-right text-sm font-bold ${stockColor}`}>{stockText}</span></div>
    </div>
  </article>;
}

function ProductFilters({ brands, categories, brand, category, stock, onBrand, onCategory, onStock, onClear }: { brands: string[]; categories: string[]; brand: string; category: string; stock: StockFilter; onBrand: (value: string) => void; onCategory: (value: string) => void; onStock: (value: StockFilter) => void; onClear: () => void }) {
  const active = [brand, category, stock !== "ALL" ? stock.replace(/_/g, " ") : ""].filter(Boolean);
  return <div className="flex min-w-0 flex-col gap-2"><div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_150px_150px_140px_auto]"><select aria-label="Filter by brand" className="field-input h-10" value={brand} onChange={(event) => onBrand(event.target.value)}><option value="">All brands</option>{brands.map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Filter by category" className="field-input h-10" value={category} onChange={(event) => onCategory(event.target.value)}><option value="">All categories</option>{categories.map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Filter by stock" className="field-input h-10" value={stock} onChange={(event) => onStock(event.target.value as StockFilter)}><option value="ALL">All stock</option><option value="IN_STOCK">In stock</option><option value="LOW_STOCK">Low stock</option><option value="OUT_OF_STOCK">Out of stock</option></select><Button type="button" variant="ghost" size="sm" disabled={!active.length} onClick={onClear}>Clear filters</Button></div></div>;
}

function PosCommandBar({ searchRef, search, loading, onSearch, onEnter, onScan, brands, categories, brand, category, stock, onBrand, onCategory, onStock, onClear, scanError }: { searchRef: { current: HTMLInputElement | null }; search: string; loading: boolean; onSearch: (value: string) => void; onEnter: () => void; onScan: (barcode: string, signal: AbortSignal) => Promise<void>; brands: string[]; categories: string[]; brand: string; category: string; stock: StockFilter; onBrand: (value: string) => void; onCategory: (value: string) => void; onStock: (value: StockFilter) => void; onClear: () => void; scanError: string }) {
  return <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"><div className="grid gap-2 lg:grid-cols-[minmax(260px,0.9fr)_minmax(0,1.4fr)]"><BarcodeScannerInput compact autoFocus label="Barcode scanner" placeholder="Scan barcode" onScan={onScan} /><div className="flex h-12 items-center rounded-xl border border-slate-200 bg-slate-50 px-3 transition focus-within:border-teal-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-teal-100"><Search size={19} className="shrink-0 text-slate-400" /><input ref={searchRef} aria-label="Search products" className="min-w-0 flex-1 border-0 bg-transparent px-3 text-sm outline-none placeholder:text-slate-400" placeholder="Search product, SKU, barcode, brand, size or color" value={search} onChange={(event) => onSearch(event.target.value)} onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => { if (event.key === "Enter") { event.preventDefault(); onEnter(); } }} />{loading ? <span className="text-xs font-semibold text-teal-700">Searching…</span> : null}{search ? <button type="button" aria-label="Clear product search" onClick={() => onSearch("")}><X size={18} className="text-slate-400" /></button> : null}</div></div><div className="mt-2 border-t border-slate-100 pt-2"><ProductFilters brands={brands} categories={categories} brand={brand} category={category} stock={stock} onBrand={onBrand} onCategory={onCategory} onStock={onStock} onClear={onClear} /></div>{scanError ? <p className="mt-2 text-sm font-medium text-rose-700">{scanError}</p> : null}</section>;
}

function ProductGroupGrid({ products, selected, onChoose, onSelectVariant }: { products: SaleCatalogProduct[]; selected: SaleCatalogProduct | null; onChoose: (product: SaleCatalogProduct) => void; onSelectVariant: (product: SaleCatalogProduct, variant: SaleCatalogVariant) => void }) {
  if (!products.length) return <div className="mt-4 rounded-2xl border border-slate-200 bg-white"><EmptyState icon={PackageOpen} title="No matching products" description="Try another search or clear one of the filters." /></div>;
  return <div className="mt-4 grid grid-cols-1 gap-3 min-[760px]:grid-cols-2">{products.map((product) => <ProductGroupCard key={product.product_id} product={product} selected={selected?.product_id === product.product_id} onChoose={() => onChoose(product)} onSelectVariant={(variant) => onSelectVariant(product, variant)} />)}</div>;
}

export function CartItemRow({ line, onChange, onSetQuantity, onRemove }: { line: CartLine; onChange: (delta: number) => void; onSetQuantity: (quantity: number) => void; onRemove: () => void }) {
  const stockAfter = Math.max(0, line.variant.available_stock - line.quantity);
  return <article className="p-4" data-testid={`cart-line-${line.variant.variant_id}`}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="line-clamp-2 break-words font-bold leading-5 text-slate-950">{line.product.name}</h3>
        <p className="mt-1 text-xs font-bold text-teal-800">Brand: {line.product.brand_name || "Unbranded"}</p>
        <p className="mt-1 text-xs text-slate-600">{line.product.category_name || "Uncategorised"} · Size: {line.variant.size || "Standard"} · Colour: {line.variant.color || "No colour"}</p>
        <p className="mt-1 text-xs text-slate-500">{line.variant.barcode ? `Barcode: ${line.variant.barcode}` : `SKU: ${line.variant.sku}`}</p>
        <p className="mt-2 text-sm text-slate-600">MRP {line.variant.mrp ? money(line.variant.mrp) : "-"} · {money(line.variant.selling_price)} × {line.quantity}</p>
      </div>
      <strong className="shrink-0 text-base text-slate-950">{money(Number(line.variant.selling_price) * line.quantity)}</strong>
    </div>
    <div className="mt-2 text-xs font-semibold text-slate-500">Available stock: {line.variant.available_stock} · Stock after sale: {stockAfter}{line.variant.scan_unit === "PACK" && (line.variant.pieces_per_pack ?? 1) > 1 ? ` · Pack scan: ${line.variant.pieces_per_pack} pieces` : ""}</div>
    <div className="mt-3 flex items-center justify-between gap-3">
      <div className="flex h-11 items-center rounded-xl border border-slate-200 bg-white">
        <button type="button" className="grid h-11 w-11 place-items-center text-slate-700 hover:bg-slate-50" onClick={() => onChange(-1)} aria-label={`Decrease ${line.product.name}`}><Minus size={17} /></button>
        <input aria-label={`Quantity for ${line.product.name}`} className="h-11 w-11 border-x border-slate-200 text-center text-sm font-bold outline-none" type="number" min="1" max={line.variant.available_stock} value={line.quantity} onChange={(event) => onSetQuantity(Number(event.target.value))} />
        <button type="button" className="grid h-11 w-11 place-items-center text-slate-700 hover:bg-slate-50" onClick={() => onChange(1)} aria-label={`Increase ${line.product.name}`}><Plus size={17} /></button>
      </div>
      <button type="button" className="text-sm font-bold text-rose-700 hover:text-rose-900" onClick={onRemove}>Remove</button>
    </div>
  </article>;
}

function CheckoutFooter({ subtotal, discountType, discountValue, preview, itemCount, lineCount, pending, onSaveBill, onSaveAndPrint }: { subtotal: number; discountType: SaleDiscountType; discountValue: string; preview: SaleDiscountPreview; itemCount: number; lineCount: number; pending: boolean; onSaveBill: () => void; onSaveAndPrint: () => void }) {
  const disabled = !lineCount || pending || !preview.valid;
  return <footer className="sticky bottom-0 z-10 shrink-0 border-t border-slate-200 bg-slate-50 p-3 shadow-[0_-8px_18px_rgba(15,23,42,0.06)]" data-testid="checkout-footer"><div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500"><span>{lineCount} product line{lineCount === 1 ? "" : "s"}</span><span>{itemCount} unit{itemCount === 1 ? "" : "s"}</span></div><div className="space-y-1.5 text-sm"><div className="flex justify-between text-slate-600"><span>Subtotal</span><span>{money(subtotal)}</span></div><div className="flex justify-between text-slate-600"><span>{saleDiscountLabel(discountType, discountValue)}</span><span>- {money(preview.discountAmount)}</span></div><div className="flex justify-between border-t border-slate-200 pt-2 text-lg font-extrabold text-slate-950"><span>Grand Total</span><span>{money(preview.total)}</span></div></div><div className="mt-3 grid grid-cols-2 gap-2"><Button type="submit" className="h-10 text-sm" disabled={disabled}><ReceiptText size={16} /> {pending ? "Saving…" : "Complete Sale"}</Button><Button type="button" variant="secondary" className="h-10 text-sm" disabled={disabled} onClick={onSaveBill}><FileText size={16} /> Save Bill</Button><Button type="button" variant="secondary" className="col-span-2 h-10 text-sm" disabled={disabled} onClick={onSaveAndPrint}><Printer size={16} /> Save &amp; Print Bill</Button></div></footer>;
}

export function CurrentSalePanel({ cart, customerName, paymentMode, discountType, discountValue, subtotal, preview, pending, onCustomer, onPayment, onDiscountType, onDiscountValue, onChangeQuantity, onSetQuantity, onRemove, onClear, onSubmit, onSaveBill, onSaveAndPrint, embedded = false }: { cart: CartLine[]; customerName: string; paymentMode: PaymentMode; discountType: SaleDiscountType; discountValue: string; subtotal: number; preview: SaleDiscountPreview; pending: boolean; onCustomer: (value: string) => void; onPayment: (value: PaymentMode) => void; onDiscountType: (value: SaleDiscountType) => void; onDiscountValue: (value: string) => void; onChangeQuantity: (variantId: string, delta: number) => void; onSetQuantity: (variantId: string, quantity: number) => void; onRemove: (variantId: string) => void; onClear: () => void; onSubmit: (event: FormEvent) => void; onSaveBill?: () => void; onSaveAndPrint?: () => void; embedded?: boolean }) {
  const itemCount = cart.reduce((totalItems, line) => totalItems + line.quantity, 0);
  return <form onSubmit={onSubmit} className={`flex h-full max-h-[min(760px,calc(100dvh-6rem))] min-h-0 w-full flex-col overflow-hidden bg-white ${embedded ? "rounded-none border-0 shadow-none" : "rounded-2xl border border-slate-200 shadow-xl"}`}>
    <header className="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3">
      <div><h2 className="flex items-center gap-2 text-lg font-extrabold text-slate-950"><ShoppingCart size={20} className="text-teal-700" /> Current Sale</h2><p className="mt-1 text-xs font-semibold text-slate-500">{cart.length} line{cart.length === 1 ? "" : "s"} · {itemCount} unit{itemCount === 1 ? "" : "s"}</p></div>
      {cart.length ? <Button type="button" variant="ghost" size="sm" className="text-rose-700" onClick={onClear}><Trash2 size={15} /> Clear</Button> : null}
    </header>
    <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto divide-y divide-slate-100 [scrollbar-gutter:stable]" data-testid="cart-item-list">
      {cart.length ? cart.map((line) => <CartItemRow key={line.variant.variant_id} line={line} onChange={(delta) => onChangeQuantity(line.variant.variant_id, delta)} onSetQuantity={(quantity) => onSetQuantity(line.variant.variant_id, quantity)} onRemove={() => onRemove(line.variant.variant_id)} />) : <div className="grid min-h-56 place-items-center p-6 text-center"><div><div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-teal-50 text-teal-700"><ShoppingBag size={25} /></div><div className="mt-3 font-bold text-slate-900">Your cart is empty</div><p className="mt-1 max-w-xs text-sm text-slate-500">Search, scan, or choose a product to start the sale.</p><p className="mt-2 text-xs font-semibold text-teal-700">Press F2 to focus product search.</p></div></div>}
    </div>
    <div className="shrink-0 space-y-2 border-t border-slate-100 px-3 py-2"><label className="field-label gap-1 text-xs">Customer <span className="text-slate-400">Optional</span><input className="field-input h-9" placeholder="Walk-in customer" value={customerName} onChange={(event) => onCustomer(event.target.value)} /></label><div><div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">Payment method</div><div className="grid grid-cols-4 gap-1.5">{paymentOptions.map((option) => { const Icon = option.icon; return <button key={option.value} type="button" onClick={() => onPayment(option.value)} className={`grid h-10 place-items-center rounded-lg border text-[11px] font-bold transition ${paymentMode === option.value ? "border-teal-600 bg-teal-50 text-teal-800 shadow-sm" : "border-slate-200 bg-white text-slate-600 hover:border-teal-200"}`}><Icon size={15} /><span>{option.label}</span></button>; })}</div></div><div className="grid grid-cols-2 gap-2"><label className="field-label gap-1 text-xs" htmlFor="sale-discount-type">Discount type<select id="sale-discount-type" aria-label="Discount type" className="field-input h-9" value={discountType} onChange={(event) => onDiscountType(event.target.value as SaleDiscountType)}><option value="PERCENTAGE">Percentage (%)</option><option value="FIXED_AMOUNT">Fixed amount (₹)</option></select></label><label className="field-label gap-1 text-xs" htmlFor="sale-discount-value">Discount value<div className="relative"><input id="sale-discount-value" aria-label="Discount value" className="field-input h-9 pr-8" inputMode="decimal" pattern="[0-9]*[.]?[0-9]{0,2}" value={discountValue} onWheel={(event) => event.currentTarget.blur()} onChange={(event) => onDiscountValue(event.target.value)} /><span className="pointer-events-none absolute inset-y-0 right-2 grid place-items-center text-sm font-bold text-slate-500">{discountType === "PERCENTAGE" ? "%" : "₹"}</span></div></label></div>{preview.error ? <p role="alert" className="text-xs font-medium text-rose-700">{preview.error}</p> : null}<div className="grid grid-cols-5 gap-1.5">{[5, 10, 15, 20].map((value) => <button key={value} type="button" className="h-8 rounded-lg border border-teal-200 bg-teal-50 text-xs font-bold text-teal-800 hover:border-teal-400" onClick={() => { onDiscountType("PERCENTAGE"); onDiscountValue(String(value)); }}>{value}%</button>)}<Button type="button" variant="ghost" size="sm" className="h-8 px-1 text-xs" disabled={discountValue === "0"} onClick={() => onDiscountValue("0")}>Clear</Button></div></div>
    <CheckoutFooter subtotal={subtotal} discountType={discountType} discountValue={discountValue} preview={preview} itemCount={itemCount} lineCount={cart.length} pending={pending} onSaveBill={onSaveBill ?? (() => undefined)} onSaveAndPrint={onSaveAndPrint ?? (() => undefined)} />
  </form>;
}

function MobileCartBar({ itemCount, total, onOpen }: { itemCount: number; total: number; onOpen: () => void }) { return <button type="button" onClick={onOpen} className="fixed inset-x-3 bottom-3 z-30 flex h-14 items-center justify-between rounded-2xl bg-primary-700 px-4 text-left text-white shadow-xl xl:hidden"><span className="flex items-center gap-2 text-sm font-bold"><ShoppingCart size={19} /> {itemCount} unit{itemCount === 1 ? "" : "s"}</span><span className="text-base font-extrabold">View sale · {money(total)}</span></button>; }

function PrintableSaleBill({ sale }: { sale: Sale }) {
  const discount = sale.discount_amount ?? sale.discount;
  return <div id="printable-invoice" className="mt-5 rounded-xl border border-slate-200 bg-white p-4 text-left"><div className="flex justify-between gap-4 border-b border-slate-200 pb-3 text-sm"><div><div className="font-extrabold text-slate-950">Rainbow Fashions</div><div className="text-slate-500">Invoice {sale.invoice_number}</div><div className="text-slate-500">Customer: {sale.customer_name || "Walk-in"}</div></div><div className="text-right text-slate-500"><div>{new Date(sale.sale_date).toLocaleString("en-IN")}</div><div>{sale.payment_mode}</div></div></div><div className="mt-3 divide-y divide-slate-100 text-sm">{sale.items.map((item) => <div key={item.id} className="flex justify-between gap-3 py-2"><span className="min-w-0"><strong className="block text-slate-900">{item.product_name}</strong><span className="text-slate-500">{item.quantity} × {money(item.unit_price)}</span></span><strong>{money(item.line_total)}</strong></div>)}</div><div className="ml-auto mt-3 grid max-w-xs grid-cols-2 gap-x-4 gap-y-1 border-t border-slate-200 pt-3 text-sm"><span>Subtotal</span><strong className="text-right">{money(sale.subtotal)}</strong><span>Discount</span><strong className="text-right">- {money(discount)}</strong><span className="font-extrabold">Grand Total</span><strong className="text-right text-base">{money(sale.grand_total ?? sale.total_amount)}</strong></div></div>;
}

export default function NewSalePage() {
  const toast = useToast(); const queryClient = useQueryClient(); const navigate = useNavigate(); const searchRef = useRef<HTMLInputElement>(null); const checkoutInFlightRef = useRef(false);
  const [search, setSearch] = useState(""); const [brandFilter, setBrandFilter] = useState(""); const [categoryFilter, setCategoryFilter] = useState(""); const [stockFilter, setStockFilter] = useState<StockFilter>("ALL");
  const [scanError, setScanError] = useState(""); const [selectedProduct, setSelectedProduct] = useState<SaleCatalogProduct | null>(null); const [cart, setCart] = useState<CartLine[]>([]); const [customerName, setCustomerName] = useState(""); const [paymentMode, setPaymentMode] = useState<PaymentMode>("CASH"); const [discountType, setDiscountType] = useState<SaleDiscountType>("PERCENTAGE"); const [discountValue, setDiscountValue] = useState("0"); const [completedSale, setCompletedSale] = useState<Sale | null>(null); const [clearOpen, setClearOpen] = useState(false); const [mobileCartOpen, setMobileCartOpen] = useState(false);
  const [sharedBarcodeChoice, setSharedBarcodeChoice] = useState<{ barcode: string; targets: Array<{ variant_id: string; product_name: string; size?: string | null; color?: string | null; current_stock: number }> } | null>(null);
  const debouncedSearch = useDebouncedValue(search, 250);
  const catalogQuery = useQuery({ queryKey: ["pos-variant-catalog", debouncedSearch], queryFn: () => api.get<SaleCatalogProduct[]>(`/sales/catalog${debouncedSearch.trim() ? `?search=${encodeURIComponent(debouncedSearch.trim())}` : ""}`) });
  const productGroups = useMemo(() => groupCatalog(catalogQuery.data ?? []), [catalogQuery.data]);
  const brands = useMemo(() => uniqueValues(productGroups.map((product) => product.brand_name)).sort(), [productGroups]);
  const categories = useMemo(() => uniqueValues(productGroups.map((product) => product.category_name)).sort(), [productGroups]);
  const filteredProducts = useMemo(() => productGroups.filter((product) => (!brandFilter || product.brand_name === brandFilter) && (!categoryFilter || product.category_name === categoryFilter) && (stockFilter === "ALL" || stockState(product) === stockFilter)), [brandFilter, categoryFilter, productGroups, stockFilter]);
  const subtotal = useMemo(() => cart.reduce((sum, line) => sum + Number(line.variant.selling_price) * line.quantity, 0), [cart]); const discountPreview = useMemo(() => previewSaleDiscount(subtotal, discountType, discountValue), [discountType, discountValue, subtotal]); const total = discountPreview.total; const itemCount = cart.reduce((sum, line) => sum + line.quantity, 0);

  useEffect(() => { const onKeyDown = (event: globalThis.KeyboardEvent) => { if (event.key === "F2") { event.preventDefault(); searchRef.current?.focus(); } }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, []);
  function addVariant(product: SaleCatalogProduct, variant: SaleCatalogVariant, quantityToAdd = 1) { const exactProduct = productForVariant(product, variant); setCart((current) => { const result = mergeCartVariant(current, exactProduct, variant, quantityToAdd); if (result.error) toast.error(result.error); return result.cart; }); setSelectedProduct(null); setSearch(""); window.requestAnimationFrame(() => searchRef.current?.focus()); }
  async function scanBarcode(value: string, signal: AbortSignal) { const targets = await api.get<Array<{ variant_id: string; product_name: string; size?: string | null; color?: string | null; current_stock: number }>>(`/barcodes/${encodeURIComponent(value)}/shared-targets`, { signal }); if (targets.length > 1) { setSharedBarcodeChoice({ barcode: value, targets }); setScanError(""); return; } const found = await api.get<ProductVariantBarcode>(`/product-variants/by-barcode/${encodeURIComponent(value)}`, { signal }); if (!found.active) throw new Error("This barcode is inactive"); if (found.package_quantity > 1 && found.sale_mode === "PIECE_ONLY") throw new Error("This package barcode is not enabled for sale"); const { product, variant } = catalogItemFromBarcode(found); setScanError(""); addVariant(product, variant, found.package_quantity); toast.success(`${found.product_name} added`); }
  function changeQuantity(variantId: string, delta: number) { setCart((current) => current.flatMap((line) => { if (line.variant.variant_id !== variantId) return [line]; const next = line.quantity + delta; if (next < 1) return [line]; if (next > line.variant.available_stock) { toast.error(`Only ${line.variant.available_stock} units available`); return [line]; } return [{ ...line, quantity: next }]; })); }
  function setQuantity(variantId: string, quantity: number) { if (!Number.isInteger(quantity) || quantity < 1) return; setCart((current) => current.map((line) => line.variant.variant_id === variantId ? { ...line, quantity: Math.min(quantity, line.variant.available_stock) } : line)); }
  function selectFirstResult() { const first = firstSellableProduct(filteredProducts); if (!first) return; const available = first.variants.filter((variant) => variant.is_active && variant.available_stock > 0); if (available.length === 1) addVariant(first, available[0]); else setSelectedProduct(first); }
  type CheckoutAction = "complete" | "save" | "print";
  const completeMutation = useMutation({ mutationFn: ({ action, idempotencyKey }: { action: CheckoutAction; idempotencyKey: string }) => { if (!cart.length) throw new Error("Add at least one product variant to the sale"); if (!discountPreview.valid) throw new Error(discountPreview.error); return api.post<Sale>("/sales", { customer_name: customerName.trim() || null, payment_mode: paymentMode, discount_type: discountType, discount_value: discountValue || "0", items: cart.map((line) => ({ product_variant_id: line.variant.variant_id, quantity: line.quantity })) }, { "Idempotency-Key": idempotencyKey }).then((sale) => ({ sale, action })); }, onSuccess: ({ sale, action }) => { setCompletedSale(sale); setCart([]); setCustomerName(""); setDiscountType("PERCENTAGE"); setDiscountValue("0"); setPaymentMode("CASH"); setMobileCartOpen(false); toast.success(`Sale ${sale.invoice_number} completed`); for (const key of ["pos-variant-catalog", "products", "sales-history", "sales-dashboard", "stock-history"]) void queryClient.invalidateQueries({ queryKey: [key] }); if (action === "print") window.requestAnimationFrame(() => window.print()); }, onError: (cause) => toast.error(cause instanceof Error ? cause.message : "Unable to complete sale"), onSettled: () => { checkoutInFlightRef.current = false; } });
  function saveCheckout(action: CheckoutAction) { if (checkoutInFlightRef.current || completeMutation.isPending) return; checkoutInFlightRef.current = true; completeMutation.mutate({ action, idempotencyKey: crypto.randomUUID() }); }
  const panelProps = { cart, customerName, paymentMode, discountType, discountValue, subtotal, preview: discountPreview, pending: completeMutation.isPending, onCustomer: setCustomerName, onPayment: setPaymentMode, onDiscountType: setDiscountType, onDiscountValue: setDiscountValue, onChangeQuantity: changeQuantity, onSetQuantity: setQuantity, onRemove: (variantId: string) => setCart((current) => current.filter((line) => line.variant.variant_id !== variantId)), onClear: () => setClearOpen(true), onSubmit: (event: FormEvent) => { event.preventDefault(); saveCheckout("complete"); }, onSaveBill: () => saveCheckout("save"), onSaveAndPrint: () => saveCheckout("print") };

  return <>
    <PageHeader title="New Sale" subtitle="Fast, accurate retail checkout" />
    <div className="grid min-w-0 gap-6 pb-20 xl:grid-cols-[minmax(0,1.85fr)_minmax(360px,1fr)] xl:pb-0">
      <section className="min-w-0">
        <PosCommandBar searchRef={searchRef} search={search} loading={catalogQuery.isFetching} onSearch={setSearch} onEnter={selectFirstResult} onScan={scanBarcode} brands={brands} categories={categories} brand={brandFilter} category={categoryFilter} stock={stockFilter} onBrand={setBrandFilter} onCategory={setCategoryFilter} onStock={setStockFilter} onClear={() => { setBrandFilter(""); setCategoryFilter(""); setStockFilter("ALL"); }} scanError={scanError} />
        {catalogQuery.isLoading ? <div className="mt-4"><SkeletonRows rows={6} /></div> : catalogQuery.error ? <div className="mt-4"><ErrorState message={catalogQuery.error instanceof Error ? catalogQuery.error.message : "Unable to load the sellable catalog"} /></div> : <ProductGroupGrid products={filteredProducts} selected={selectedProduct} onChoose={setSelectedProduct} onSelectVariant={addVariant} />}
      </section>
      <aside className="hidden xl:sticky xl:top-20 xl:block xl:h-[calc(100dvh-6rem)] xl:min-h-0"><CurrentSalePanel {...panelProps} /></aside>
    </div>
    <MobileCartBar itemCount={itemCount} total={total} onOpen={() => setMobileCartOpen(true)} />
    <Dialog open={mobileCartOpen} title="Current Sale" description={`${cart.length} product lines · ${itemCount} units`} onClose={() => setMobileCartOpen(false)} maxWidth="lg" fullHeight contentClassName="min-h-0 flex-1 overflow-hidden p-0"><CurrentSalePanel {...panelProps} embedded /></Dialog>
    <Dialog open={Boolean(selectedProduct)} title={selectedProduct?.name ?? "Choose variant"} description={`${selectedProduct?.brand_name || "Unbranded"} · Select the exact size and colour`} onClose={() => setSelectedProduct(null)} maxWidth="xl">
      <div className="mb-4 flex items-center gap-3 rounded-xl bg-slate-50 p-3">{selectedProduct ? <ProductVisual product={selectedProduct} /> : null}<div><div className="font-bold">{selectedProduct?.name}</div><div className="text-sm text-slate-500">{selectedProduct?.category_name} · {selectedProduct?.brand_name}</div></div></div>
      <div className="grid gap-3 sm:grid-cols-2">{selectedProduct ? orderVariantsBySize(selectedProduct.variants).map((variant) => { const low = variant.available_stock > 0 && selectedProduct.minimum_stock > 0 && variant.available_stock < selectedProduct.minimum_stock; return <button key={variant.variant_id} type="button" disabled={!variant.available_stock || !variant.is_active} onClick={() => addVariant(selectedProduct, variant)} className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-teal-500 hover:bg-teal-50 focus-visible:ring-2 focus-visible:ring-teal-500 disabled:cursor-not-allowed disabled:opacity-50"><div className="flex justify-between gap-3"><strong>{variantLabel(variant)}</strong><span className={`rounded-full px-2 py-1 text-xs font-bold ${!variant.available_stock ? "bg-rose-100 text-rose-800" : low ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}>{!variant.available_stock ? "Out of stock" : low ? `Low · ${variant.available_stock}` : `${variant.available_stock} in stock`}</span></div><div className="mt-2 text-xs text-slate-500">SKU {variant.sku} · {variant.barcode}</div><div className="mt-3 flex items-center justify-between"><span className="text-sm">MRP {variant.mrp ? money(variant.mrp) : "-"}</span><strong className="text-teal-800">{money(variant.selling_price)}</strong></div><div className="mt-3 text-sm font-bold text-teal-800">Add to sale →</div></button>; }) : null}</div>
    </Dialog>
    <ConfirmDialog open={clearOpen} title="Clear current sale" description="Remove every item from this sale?" confirmLabel="Clear cart" onCancel={() => setClearOpen(false)} onConfirm={() => { setCart([]); setDiscountType("PERCENTAGE"); setDiscountValue("0"); setClearOpen(false); }} />
    <Dialog open={Boolean(sharedBarcodeChoice)} onClose={() => setSharedBarcodeChoice(null)} title="Shared barcode detected" description="Choose the exact size to add. Stock stays separate for each size.">{sharedBarcodeChoice ? <div className="space-y-2"><p className="font-mono text-sm text-slate-600">{sharedBarcodeChoice.barcode}</p>{sharedBarcodeChoice.targets.map((target) => <Button key={target.variant_id} type="button" variant="secondary" className="h-auto w-full justify-between py-3" onClick={() => { const product = productGroups.find((candidate) => candidate.variants.some((variant) => variant.variant_id === target.variant_id)); const variant = product?.variants.find((candidate) => candidate.variant_id === target.variant_id); if (!product || !variant) { setScanError("Refresh the product list and select the size again."); return; } addVariant(product, variant); setSharedBarcodeChoice(null); toast.success(`${target.product_name} / ${target.size || "Standard"} added`); }}><span><strong>{target.size || "Standard"}{target.color ? ` · ${target.color}` : ""}</strong><span className="ml-2 text-xs text-slate-500">{target.current_stock} in stock</span></span></Button>)}</div> : null}</Dialog>
    <Dialog open={Boolean(completedSale)} title="Sale completed" description={completedSale?.invoice_number} onClose={() => setCompletedSale(null)} maxWidth="md">
      {completedSale ? <div className="text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 size={34} /></div><div className="mt-4 text-3xl font-bold">{money(completedSale.total_amount)}</div><p className="mt-1 text-sm text-slate-500">Payment received by {completedSale.payment_mode}</p><PrintableSaleBill sale={completedSale} /><div className="mt-5 grid gap-2 sm:grid-cols-2"><Button type="button" variant="secondary" onClick={() => window.print()}><Printer size={16} /> Print Bill</Button><Button type="button" variant="secondary" onClick={() => { navigate(`/sales/history?invoice_number=${encodeURIComponent(completedSale.invoice_number)}`); setCompletedSale(null); }}><FileText size={16} /> View invoice</Button><Button type="button" className="sm:col-span-2" onClick={() => setCompletedSale(null)}>Start new sale</Button></div></div> : null}
    </Dialog>
  </>;
}

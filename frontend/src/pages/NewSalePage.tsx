import { FormEvent, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, CheckCircle2, CreditCard, Minus, PackageOpen, Plus, ReceiptText, Search, ShoppingCart, Smartphone, Trash2, WalletCards, X } from "lucide-react";
import { api } from "../api/client";
import Dialog from "../components/Dialog";
import BarcodeScannerInput from "../components/BarcodeScannerInput";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import type { ProductVariantBarcode, Sale, SaleCatalogProduct, SaleCatalogVariant } from "../types";
import { money } from "../utils/format";

type PaymentMode = "CASH" | "UPI" | "CARD" | "BANK" | "OTHER";
interface CartLine { product: SaleCatalogProduct; variant: SaleCatalogVariant; quantity: number }

const paymentOptions: Array<{ value: PaymentMode; label: string; icon: typeof Banknote }> = [
  { value: "CASH", label: "Cash", icon: Banknote },
  { value: "UPI", label: "UPI", icon: Smartphone },
  { value: "CARD", label: "Card", icon: CreditCard },
  { value: "BANK", label: "Bank", icon: WalletCards },
];

function variantLabel(variant: SaleCatalogVariant) {
  return [variant.size, variant.color, variant.style_code].filter(Boolean).join(" / ") || variant.sku;
}

const brandBadgeTones = [
  "bg-teal-50 text-teal-800 ring-teal-200 shadow-teal-100",
  "bg-sky-50 text-sky-800 ring-sky-200 shadow-sky-100",
  "bg-violet-50 text-violet-800 ring-violet-200 shadow-violet-100",
  "bg-amber-50 text-amber-800 ring-amber-200 shadow-amber-100",
  "bg-rose-50 text-rose-800 ring-rose-200 shadow-rose-100",
];

function brandBadgeTone(brandName?: string | null) {
  const value = (brandName || "").split("").reduce((total, character) => total + character.charCodeAt(0), 0);
  return brandBadgeTones[value % brandBadgeTones.length];
}

function ProductIdentity({ product }: { product: SaleCatalogProduct }) {
  const [imageFailed, setImageFailed] = useState(false);
  const imageUrl = product.brand_logo_url || product.product_image_url;
  const initials = (product.brand_name || product.name).split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
  return imageUrl && !imageFailed ? <img src={imageUrl} alt={product.brand_name ? `${product.brand_name} logo` : product.name} className="h-12 w-12 shrink-0 rounded-xl border border-teal-100 bg-white object-contain p-1" onError={() => setImageFailed(true)} /> : <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-teal-50 text-sm font-bold text-teal-700">{initials || <PackageOpen size={21} />}</div>;
}

export default function NewSalePage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const searchRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [scanError, setScanError] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<SaleCatalogProduct | null>(null);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [paymentMode, setPaymentMode] = useState<PaymentMode>("CASH");
  const [discount, setDiscount] = useState("0");
  const [error, setError] = useState("");
  const [completedSale, setCompletedSale] = useState<Sale | null>(null);
  const debouncedSearch = useDebouncedValue(search, 300);

  const catalogQuery = useQuery({
    queryKey: ["pos-variant-catalog", debouncedSearch],
    queryFn: () => api.get<SaleCatalogProduct[]>(`/sales/catalog${debouncedSearch.trim() ? `?search=${encodeURIComponent(debouncedSearch.trim())}` : ""}`),
  });
  const catalog = catalogQuery.data ?? [];
  const subtotal = useMemo(() => cart.reduce((sum, line) => sum + Number(line.variant.selling_price) * line.quantity, 0), [cart]);
  const discountAmount = Number(discount) || 0;
  const total = Math.max(0, subtotal - discountAmount);
  const itemCount = cart.reduce((sum, line) => sum + line.quantity, 0);

  function addVariant(product: SaleCatalogProduct, variant: SaleCatalogVariant, quantityToAdd = 1, focusTarget: HTMLInputElement | null = searchRef.current) {
    if (!variant.is_active || variant.available_stock <= 0) {
      toast.error(`${product.name} (${variantLabel(variant)}) is out of stock`);
      return;
    }
    setError("");
    setCart((current) => {
      const existing = current.find((line) => line.variant.variant_id === variant.variant_id);
      if (existing) {
        if (existing.quantity + quantityToAdd > variant.available_stock) {
          toast.error(`Only ${variant.available_stock} units available`);
          return current;
        }
        return current.map((line) => line.variant.variant_id === variant.variant_id ? { ...line, quantity: line.quantity + quantityToAdd } : line);
      }
      if (quantityToAdd > variant.available_stock) { toast.error(`Only ${variant.available_stock} units available`); return current; }
      return [...current, { product, variant, quantity: quantityToAdd }];
    });
    setSelectedProduct(null);
    setSearch("");
    focusTarget?.focus();
  }

  async function scanBarcode(value: string, signal: AbortSignal) {
    const found = await api.get<ProductVariantBarcode>(`/product-variants/by-barcode/${encodeURIComponent(value)}`, { signal });
    if (!found.active) throw new Error("This barcode is inactive");
    if (found.package_quantity > 1 && found.sale_mode === "PIECE_ONLY") throw new Error("This package barcode is not enabled for sale");
    const variant: SaleCatalogVariant = { variant_id: found.variant_id, size: found.size, color: found.color, style_code: found.style_code, sku: found.sku, barcode: found.barcode, mrp: found.mrp, selling_price: found.selling_price, available_stock: found.current_available_stock, classification_review_required: false, is_active: found.active };
    const product: SaleCatalogProduct = { product_id: found.product_id, name: found.product_name, category_name: found.category, brand_name: found.brand, variant_count: 1, total_stock: found.current_available_stock, minimum_stock: 0, total_available_stock: found.current_available_stock, variants: [variant] };
    setScanError("");
    addVariant(product, variant, found.package_quantity);
    toast.success(`${found.product_name} added${found.package_quantity > 1 ? ` (${found.package_quantity} pieces)` : ""}`);
  }

  function changeQuantity(variantId: string, change: number) {
    setCart((current) => current.flatMap((line) => {
      if (line.variant.variant_id !== variantId) return [line];
      const next = line.quantity + change;
      if (next <= 0) return [];
      if (next > line.variant.available_stock) { toast.error(`Only ${line.variant.available_stock} units available`); return [line]; }
      return [{ ...line, quantity: next }];
    }));
  }

  const completeMutation = useMutation({
    mutationFn: () => {
      if (!cart.length) throw new Error("Add at least one product variant to the sale");
      if (!Number.isFinite(discountAmount) || discountAmount < 0) throw new Error("Discount cannot be negative");
      if (discountAmount > subtotal) throw new Error("Discount cannot exceed subtotal");
      return api.post<Sale>("/sales", { customer_name: customerName.trim() || null, payment_mode: paymentMode, discount: discountAmount, items: cart.map((line) => ({ product_variant_id: line.variant.variant_id, quantity: line.quantity })) });
    },
    onSuccess: (sale) => {
      setCompletedSale(sale); setCart([]); setCustomerName(""); setDiscount("0"); setPaymentMode("CASH"); setError("");
      toast.success(`Sale ${sale.invoice_number} completed`);
      for (const key of ["pos-variant-catalog", "products", "sales-history", "sales-dashboard", "stock-history"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to complete sale"; setError(message); toast.error(message); },
  });

  function submit(event: FormEvent) { event.preventDefault(); completeMutation.mutate(); }

  return <>
    <PageHeader title="New Sale" subtitle="Select the exact size, style, barcode and price before adding it to the cart" />
    <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
      <section className="min-w-0">
        <div className="mb-4"><BarcodeScannerInput autoFocus label="Barcode scanner" placeholder="Scan an exact variant barcode and press Enter" onScan={scanBarcode} />{scanError ? <p className="mt-2 text-sm font-medium text-rose-700">{scanError}</p> : null}</div>
        <div className="mb-4 flex h-12 items-center rounded-lg border border-slate-200 bg-white px-4 shadow-sm"><Search size={19} className="shrink-0 text-slate-400" /><input ref={searchRef} aria-label="Search products" className="min-w-0 flex-1 border-0 px-3 outline-none" placeholder="Search product, SKU, style or barcode" value={search} onChange={(event) => setSearch(event.target.value)} />{search ? <button type="button" onClick={() => setSearch("")} aria-label="Clear product search"><X size={18} className="text-slate-400" /></button> : null}</div>
        {catalogQuery.isLoading ? <SkeletonRows rows={6} /> : catalogQuery.error ? <ErrorState message={catalogQuery.error instanceof Error ? catalogQuery.error.message : "Unable to load the sellable catalog"} /> : catalog.length ? <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">{catalog.map((product) => {
          const lowStock = product.minimum_stock > 0 && product.total_stock < product.minimum_stock;
          const brandTone = brandBadgeTone(product.brand_name);
          return <button key={product.product_id} type="button" disabled={product.total_available_stock <= 0} onClick={() => product.variants.length === 1 ? addVariant(product, product.variants[0]) : setSelectedProduct(product)} className="group flex min-h-32 items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 disabled:cursor-not-allowed disabled:opacity-55">
            <ProductIdentity product={product} />
            <div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-2"><div className="truncate font-bold text-slate-950">{product.name}</div>{product.brand_name ? <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ring-1 ring-inset shadow-sm ${brandTone}`}>{product.brand_name}</span> : null}</div><div className="mt-1 truncate text-xs text-slate-500">{[product.category_name, product.brand_name].filter(Boolean).join(" · ")}</div><div className="mt-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs"><span className="font-semibold text-teal-800">{product.variant_count} variant{product.variant_count === 1 ? "" : "s"}</span><span className={lowStock ? "rounded-full bg-amber-100 px-2 py-1 font-bold text-amber-800" : product.total_stock ? "font-semibold text-slate-600" : "font-semibold text-red-600"}>{lowStock ? `Low stock · ${product.total_stock}` : `${product.total_stock} in stock`}</span></div></div>
          </button>;
        })}</div> : <div className="rounded-lg border border-slate-200 bg-white"><EmptyState icon={PackageOpen} title="No sellable variants found" description="Confirm purchase items first, then try product name, SKU, style or barcode." /></div>}
      </section>

      <form onSubmit={submit} className="ds-surface h-fit overflow-hidden shadow-lg xl:sticky xl:top-20"><div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="flex items-center gap-2 text-lg font-semibold"><ShoppingCart size={20} /> Current Sale</h2><p className="mt-1 text-xs text-slate-500">{itemCount} items</p></div>{cart.length ? <Button type="button" variant="ghost" size="sm" onClick={() => setCart([])}><Trash2 size={15} /> Clear</Button> : null}</div><div className="max-h-[340px] divide-y divide-slate-100 overflow-y-auto">{cart.map((line) => <div key={line.variant.variant_id} className="p-4"><div className="flex justify-between gap-3"><div className="min-w-0"><div className="truncate font-semibold text-slate-900">{line.product.name}</div><div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset shadow-sm ${brandBadgeTone(line.product.brand_name)}`}>{line.product.brand_name || "Unbranded"}</div><div className="mt-1 text-xs text-slate-500">Size: {line.variant.size || "Standard"} · Colour: {line.variant.color || "-"}</div><div className="text-xs text-slate-500">Unit price: {money(line.variant.selling_price)}</div></div><strong>{money(Number(line.variant.selling_price) * line.quantity)}</strong></div><div className="mt-3 flex items-center justify-between"><div className="flex items-center gap-2"><div className="flex items-center rounded-lg border border-slate-200"><button type="button" className="grid h-9 w-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => changeQuantity(line.variant.variant_id, -1)} aria-label={`Decrease ${line.product.name}`}><Minus size={15} /></button><span className="w-9 text-center text-sm font-bold">{line.quantity}</span><button type="button" className="grid h-9 w-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => changeQuantity(line.variant.variant_id, 1)} aria-label={`Increase ${line.product.name}`}><Plus size={15} /></button></div><span className="text-xs font-semibold text-slate-500">Qty {line.quantity}</span></div><button type="button" className="text-red-500 hover:text-red-700" onClick={() => setCart((current) => current.filter((item) => item.variant.variant_id !== line.variant.variant_id))} aria-label={`Remove ${line.product.name}`}><Trash2 size={17} /></button></div></div>)}{!cart.length ? <EmptyState icon={ShoppingCart} title="Your cart is empty" description="Choose a product, then select its exact variant." /> : null}</div><div className="space-y-4 border-t border-slate-100 bg-slate-50/60 p-5"><label className="field-label">Customer <span className="!ml-1 !text-xs !font-normal !text-slate-400">Optional</span><input className="field-input" placeholder="Walk-in customer" value={customerName} onChange={(event) => setCustomerName(event.target.value)} /></label><div><div className="mb-2 text-sm font-semibold text-slate-700">Payment method</div><div className="grid grid-cols-4 gap-2">{paymentOptions.map((option) => { const Icon = option.icon; return <button key={option.value} type="button" onClick={() => setPaymentMode(option.value)} className={`grid min-h-14 place-items-center rounded-lg border px-1 py-2 text-xs font-semibold transition ${paymentMode === option.value ? "border-teal-600 bg-teal-50 text-teal-800" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"}`}><Icon size={18} /><span>{option.label}</span></button>; })}</div></div><label className="field-label">Discount<input className="field-input" type="number" min="0" max={subtotal} step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label><div className="space-y-2 border-t border-slate-200 pt-4 text-sm"><div className="flex justify-between text-slate-600"><span>Subtotal</span><span>{money(subtotal)}</span></div><div className="flex justify-between text-slate-600"><span>Discount</span><span>- {money(discountAmount)}</span></div><div className="flex justify-between pt-2 text-xl font-bold text-slate-950"><span>Total</span><span>{money(total)}</span></div></div>{error ? <ErrorState message={error} /> : null}<Button type="submit" className="w-full" disabled={!cart.length || completeMutation.isPending}><ReceiptText size={18} /> {completeMutation.isPending ? "Completing Sale" : `Complete Sale · ${money(total)}`}</Button></div></form>
    </div>
    <Dialog open={Boolean(selectedProduct)} title={selectedProduct?.name ?? "Choose variant"} description="Select the exact size, style and price for this sale." onClose={() => setSelectedProduct(null)} maxWidth="lg"><div className="grid gap-3 sm:grid-cols-2">{selectedProduct?.variants.map((variant) => <button key={variant.variant_id} type="button" disabled={!variant.available_stock || !variant.is_active} onClick={() => selectedProduct && addVariant(selectedProduct, variant)} className="rounded-lg border border-slate-200 p-4 text-left transition hover:border-teal-500 hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-50"><div className="font-semibold text-slate-900">{variantLabel(variant)}</div><div className="mt-1 text-xs text-slate-500">SKU: {variant.sku} · Barcode: {variant.barcode}</div><div className="mt-3 flex justify-between text-sm"><span>MRP {variant.mrp ? money(variant.mrp) : "-"}</span><strong>{money(variant.selling_price)}</strong></div><div className="mt-2 text-xs font-semibold text-teal-800">{variant.available_stock} available</div>{variant.classification_review_required ? <div className="mt-2 text-xs text-amber-700">Review temporary style label before the next purchase.</div> : null}</button>)}</div></Dialog>
    <Dialog open={Boolean(completedSale)} title="Sale completed" description={completedSale?.invoice_number} onClose={() => setCompletedSale(null)} maxWidth="md">{completedSale ? <div className="text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 size={34} /></div><div className="mt-4 text-3xl font-bold">{money(completedSale.total_amount)}</div><p className="mt-1 text-sm text-slate-500">Payment received by {completedSale.payment_mode}</p><Button type="button" className="mt-5 w-full" onClick={() => setCompletedSale(null)}>Start next sale</Button></div> : null}</Dialog>
  </>;
}

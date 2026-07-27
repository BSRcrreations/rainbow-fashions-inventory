import { FormEvent, KeyboardEvent, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, CheckCircle2, CreditCard, Minus, PackageOpen, Plus, ReceiptText, Search, ShoppingCart, Smartphone, Trash2, WalletCards, X } from "lucide-react";
import { api } from "../api/client";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import type { Product, Sale } from "../types";
import { money, shortDate } from "../utils/format";
import { productVariantLabel } from "../utils/product";

type PaymentMode = "CASH" | "UPI" | "CARD" | "BANK" | "OTHER";
interface CartLine { product: Product; quantity: number }

const paymentOptions: Array<{ value: PaymentMode; label: string; icon: typeof Banknote }> = [
  { value: "CASH", label: "Cash", icon: Banknote },
  { value: "UPI", label: "UPI", icon: Smartphone },
  { value: "CARD", label: "Card", icon: CreditCard },
  { value: "BANK", label: "Bank", icon: WalletCards },
];

export default function NewSalePage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const searchRef = useRef<HTMLInputElement>(null);
  const barcodeRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [barcode, setBarcode] = useState("");
  const [scannedProduct, setScannedProduct] = useState<Product | null>(null);
  const [scanError, setScanError] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [paymentMode, setPaymentMode] = useState<PaymentMode>("CASH");
  const [discount, setDiscount] = useState("0");
  const [error, setError] = useState("");
  const [completedSale, setCompletedSale] = useState<Sale | null>(null);

  const productsQuery = useQuery({
    queryKey: ["pos-products", debouncedSearch],
    queryFn: () => api.get<Product[]>(`/products?limit=50&is_active=true${debouncedSearch.trim() ? `&search=${encodeURIComponent(debouncedSearch.trim())}` : ""}`),
  });
  const products = productsQuery.data ?? [];
  const subtotal = useMemo(() => cart.reduce((sum, line) => sum + Number(line.product.selling_price) * line.quantity, 0), [cart]);
  const discountAmount = Number(discount) || 0;
  const total = Math.max(0, subtotal - discountAmount);
  const itemCount = cart.reduce((sum, line) => sum + line.quantity, 0);

  function addProduct(product: Product, focusTarget: HTMLInputElement | null = searchRef.current) {
    if (product.current_stock <= 0) { toast.error(`${product.name} is out of stock`); return; }
    setError("");
    setCart((current) => {
      const existing = current.find((line) => line.product.id === product.id);
      if (existing) {
        if (existing.quantity >= product.current_stock) { toast.error(`Only ${product.current_stock} units available`); return current; }
        return current.map((line) => line.product.id === product.id ? { ...line, quantity: line.quantity + 1 } : line);
      }
      return [...current, { product, quantity: 1 }];
    });
    setSearch("");
    focusTarget?.focus();
  }

  const scanMutation = useMutation({
    mutationFn: (value: string) => api.get<Product>(`/products/barcode/${encodeURIComponent(value)}`),
    onSuccess: (product) => {
      setScannedProduct(product);
      if (!product.is_active) {
        setScanError(`${product.name} is inactive and cannot be sold`);
        return;
      }
      if (product.current_stock <= 0) {
        setScanError(`${product.name} is out of stock`);
        return;
      }
      setScanError("");
      addProduct(product, barcodeRef.current);
    },
    onError: (cause) => {
      setScannedProduct(null);
      const message = cause instanceof Error ? cause.message : "Unknown barcode";
      setScanError(message.toLowerCase().includes("not found") ? "Unknown barcode. Check the label and try again." : message);
    },
    onSettled: () => {
      setBarcode("");
      window.requestAnimationFrame(() => barcodeRef.current?.focus());
    },
  });

  function scanBarcode() {
    const value = barcode.trim();
    if (!value || scanMutation.isPending) return;
    setScanError("");
    scanMutation.mutate(value);
  }

  function onBarcodeKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    scanBarcode();
  }

  function changeQuantity(productId: string, change: number) {
    setCart((current) => current.flatMap((line) => {
      if (line.product.id !== productId) return [line];
      const next = line.quantity + change;
      if (next <= 0) return [];
      if (next > line.product.current_stock) { toast.error(`Only ${line.product.current_stock} units available`); return [line]; }
      return [{ ...line, quantity: next }];
    }));
  }

  const completeMutation = useMutation({
    mutationFn: () => {
      if (!cart.length) throw new Error("Add at least one product to the sale");
      if (!Number.isFinite(discountAmount) || discountAmount < 0) throw new Error("Discount cannot be negative");
      if (discountAmount > subtotal) throw new Error("Discount cannot exceed subtotal");
      return api.post<Sale>("/sales", {
        customer_name: customerName.trim() || null,
        payment_mode: paymentMode,
        discount: discountAmount,
        items: cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity })),
      });
    },
    onSuccess: (sale) => {
      setCompletedSale(sale);
      setCart([]);
      setCustomerName("");
      setDiscount("0");
      setPaymentMode("CASH");
      setError("");
      toast.success(`Sale ${sale.invoice_number} completed`);
      void queryClient.invalidateQueries({ queryKey: ["pos-products"] });
      void queryClient.invalidateQueries({ queryKey: ["products"] });
      void queryClient.invalidateQueries({ queryKey: ["sales-history"] });
      void queryClient.invalidateQueries({ queryKey: ["sales-dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["stock-history"] });
    },
    onError: (cause) => { const message = cause instanceof Error ? cause.message : "Unable to complete sale"; setError(message); toast.error(message); },
  });

  function submit(event: FormEvent) { event.preventDefault(); completeMutation.mutate(); }

  return (
    <>
      <PageHeader title="New Sale" subtitle="Search or scan products, build the cart, and complete checkout" />
      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <section className="min-w-0">
          <div className="mb-4 rounded-lg border border-primary-200 bg-primary-50/60 p-3 shadow-sm"><label className="flex items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary-700 text-white"><PackageOpen size={19} /></div><div className="min-w-0 flex-1"><div className="text-sm font-semibold text-foreground">Barcode scanner</div><input ref={barcodeRef} autoFocus aria-label="Scan product barcode" className="mt-1 w-full border-0 bg-transparent p-0 text-sm outline-none placeholder:text-slate-400" placeholder="Scan barcode and press Enter" value={barcode} onChange={(event) => setBarcode(event.target.value)} onKeyDown={onBarcodeKeyDown} autoComplete="off" /></div>{scanMutation.isPending ? <span className="text-xs font-semibold text-primary-700">Looking up</span> : null}</label>{scanError ? <p className="mt-2 text-sm font-medium text-rose-700">{scanError}</p> : null}{scannedProduct ? <div className="mt-3 grid gap-2 border-t border-primary-100 pt-3 text-xs text-slate-700 sm:grid-cols-2"><span><strong>{scannedProduct.name}</strong> · {productVariantLabel(scannedProduct)}</span><span>Barcode: {scannedProduct.barcode ?? "-"}</span><span>Date: {shortDate(scannedProduct.product_date)}</span><span>{money(scannedProduct.selling_price)} · {scannedProduct.current_stock} available</span></div> : null}</div>
          <div className="mb-4 flex h-12 items-center rounded-lg border border-slate-200 bg-white px-4 shadow-sm"><Search size={19} className="shrink-0 text-slate-400" /><input ref={searchRef} aria-label="Search products" className="min-w-0 flex-1 border-0 px-3 outline-none" placeholder="Search product, SKU, brand, or category" value={search} onChange={(event) => setSearch(event.target.value)} />{search ? <button type="button" onClick={() => setSearch("")} aria-label="Clear product search"><X size={18} className="text-slate-400" /></button> : null}</div>
          {productsQuery.isLoading ? <SkeletonRows rows={6} /> : productsQuery.error ? <ErrorState message={productsQuery.error instanceof Error ? productsQuery.error.message : "Unable to load products"} /> : products.length ? (
            <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">{products.map((product) => <button key={product.id} type="button" disabled={product.current_stock <= 0} onClick={() => addProduct(product)} className="group flex min-h-28 items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-55"><div className="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-400"><PackageOpen size={21} /></div><div className="min-w-0 flex-1"><div className="truncate font-semibold text-slate-950">{product.name}</div><div className="mt-1 truncate text-xs text-slate-500">{productVariantLabel(product)} · {product.brand?.name}</div><div className="mt-3 flex items-center justify-between gap-2"><strong className="text-teal-800">{money(product.selling_price)}</strong><span className={`text-xs font-semibold ${product.current_stock ? "text-slate-500" : "text-red-600"}`}>{product.current_stock ? `${product.current_stock} in stock` : "Out of stock"}</span></div></div></button>)}</div>
          ) : <div className="rounded-lg border border-slate-200 bg-white"><EmptyState icon={PackageOpen} title="No products found" description="Try a product name, SKU, barcode, brand, or category." /></div>}
        </section>

        <form onSubmit={submit} className="ds-surface h-fit overflow-hidden shadow-lg xl:sticky xl:top-20">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="flex items-center gap-2 text-lg font-semibold"><ShoppingCart size={20} /> Current Sale</h2><p className="mt-1 text-xs text-slate-500">{itemCount} items</p></div>{cart.length ? <Button type="button" variant="ghost" size="sm" onClick={() => setCart([])}><Trash2 size={15} /> Clear</Button> : null}</div>
          <div className="max-h-[340px] overflow-y-auto divide-y divide-slate-100">{cart.map((line) => <div key={line.product.id} className="p-4"><div className="flex justify-between gap-3"><div className="min-w-0"><div className="truncate font-semibold text-slate-900">{line.product.name}</div><div className="mt-0.5 text-xs text-slate-500">{productVariantLabel(line.product)} · {money(line.product.selling_price)}</div></div><strong>{money(Number(line.product.selling_price) * line.quantity)}</strong></div><div className="mt-3 flex items-center justify-between"><div className="flex items-center rounded-lg border border-slate-200"><button type="button" className="grid h-9 w-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => changeQuantity(line.product.id, -1)} aria-label={`Decrease ${line.product.name}`}><Minus size={15} /></button><span className="w-9 text-center text-sm font-bold">{line.quantity}</span><button type="button" className="grid h-9 w-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => changeQuantity(line.product.id, 1)} aria-label={`Increase ${line.product.name}`}><Plus size={15} /></button></div><button type="button" className="text-red-500 hover:text-red-700" onClick={() => setCart((current) => current.filter((item) => item.product.id !== line.product.id))} aria-label={`Remove ${line.product.name}`}><Trash2 size={17} /></button></div></div>)}{!cart.length ? <EmptyState icon={ShoppingCart} title="Your cart is empty" description="Select a product to start a new sale." /> : null}</div>
          <div className="space-y-4 border-t border-slate-100 bg-slate-50/60 p-5"><label className="field-label">Customer <span className="!ml-1 !text-xs !font-normal !text-slate-400">Optional</span><input className="field-input" placeholder="Walk-in customer" value={customerName} onChange={(event) => setCustomerName(event.target.value)} /></label><div><div className="mb-2 text-sm font-semibold text-slate-700">Payment method</div><div className="grid grid-cols-4 gap-2">{paymentOptions.map((option) => { const Icon = option.icon; return <button key={option.value} type="button" onClick={() => setPaymentMode(option.value)} className={`grid min-h-14 place-items-center rounded-lg border px-1 py-2 text-xs font-semibold transition ${paymentMode === option.value ? "border-teal-600 bg-teal-50 text-teal-800" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"}`}><Icon size={18} /><span>{option.label}</span></button>; })}</div></div><label className="field-label">Discount<input className="field-input" type="number" min="0" max={subtotal} step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label><div className="space-y-2 border-t border-slate-200 pt-4 text-sm"><div className="flex justify-between text-slate-600"><span>Subtotal</span><span>{money(subtotal)}</span></div><div className="flex justify-between text-slate-600"><span>Discount</span><span>- {money(discountAmount)}</span></div><div className="flex justify-between pt-2 text-xl font-bold text-slate-950"><span>Total</span><span>{money(total)}</span></div></div>{error ? <ErrorState message={error} /> : null}<Button type="submit" className="w-full" disabled={!cart.length || completeMutation.isPending}><ReceiptText size={18} /> {completeMutation.isPending ? "Completing Sale" : `Complete Sale · ${money(total)}`}</Button></div>
        </form>
      </div>

      <Dialog open={Boolean(completedSale)} title="Sale completed" description={completedSale?.invoice_number} onClose={() => setCompletedSale(null)} maxWidth="md">{completedSale ? <div className="text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 size={34} /></div><div className="mt-4 text-3xl font-bold">{money(completedSale.total_amount)}</div><p className="mt-1 text-sm text-slate-500">Payment received by {completedSale.payment_mode}</p><div className="mt-5 rounded-lg bg-slate-50 p-4 text-left text-sm"><div className="flex justify-between"><span>Invoice</span><strong>{completedSale.invoice_number}</strong></div><div className="mt-2 flex justify-between"><span>Items</span><strong>{completedSale.items.reduce((sum, item) => sum + item.quantity, 0)}</strong></div></div><Button type="button" className="mt-5 w-full" onClick={() => setCompletedSale(null)}>Start next sale</Button></div> : null}</Dialog>
    </>
  );
}

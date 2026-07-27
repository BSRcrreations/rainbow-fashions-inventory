import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Minus, Plus, Save, Search, Trash2, XCircle } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useAuth } from "../hooks/useAuth";
import type { Product, Sale } from "../types";
import { money } from "../utils/format";

type CartLine = { product: Product; quantity: number; unitPrice: number };

export default function EditSalePage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [reason, setReason] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [paymentMode, setPaymentMode] = useState("CASH");
  const [discount, setDiscount] = useState("0");
  const [cart, setCart] = useState<CartLine[] | null>(null);
  const [inlineError, setInlineError] = useState("");
  const [voidOpen, setVoidOpen] = useState(false);
  const [voidReason, setVoidReason] = useState("");
  const saleQuery = useQuery({ queryKey: ["sale", saleId], queryFn: () => api.get<Sale>(`/sales/${saleId}`), enabled: Boolean(saleId) });
  const sale = saleQuery.data;
  const debouncedSearch = useDebouncedValue(search, 300);
  const productsQuery = useQuery({ queryKey: ["edit-sale-products", debouncedSearch], queryFn: () => api.get<Product[]>(`/products?limit=30&is_active=true${debouncedSearch ? `&search=${encodeURIComponent(debouncedSearch)}` : ""}`) });
  const lines = useMemo(() => cart ?? (sale ? sale.items.map((item) => ({ product: { id: item.product_id, name: item.product_name, current_stock: 0, selling_price: item.unit_price } as Product, quantity: item.quantity, unitPrice: Number(item.unit_price) })) : []), [cart, sale]);
  const selectedCustomer = cart === null && sale ? sale.customer_name ?? "" : customerName;
  const selectedPayment = cart === null && sale ? sale.payment_mode : paymentMode;
  const selectedDiscount = cart === null && sale ? String(sale.discount) : discount;
  const subtotal = useMemo(() => lines.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0), [lines]);
  const total = Math.max(0, subtotal - (Number(selectedDiscount) || 0));
  const originalQuantities = new Map(sale?.items.map((item) => [item.product_id, item.quantity]));
  const canVoid = user?.role === "OWNER" || user?.role === "MANAGER";

  function updateLines(change: (current: CartLine[]) => CartLine[]) { setInlineError(""); setCart(change(lines)); }
  function changeQuantity(productId: string, amount: number) { updateLines((current) => current.flatMap((line) => line.product.id === productId ? line.quantity + amount <= 0 ? [] : [{ ...line, quantity: line.quantity + amount }] : [line])); }
  function addProduct(product: Product) { updateLines((current) => { const existing = current.find((line) => line.product.id === product.id); return existing ? current.map((line) => line.product.id === product.id ? { ...line, quantity: line.quantity + 1 } : line) : [...current, { product, quantity: 1, unitPrice: Number(product.selling_price) }]; }); setSearch(""); }

  const mutation = useMutation({
    mutationFn: () => {
      if (!saleId || !sale) throw new Error("Sale is unavailable");
      if (reason.trim().length < 3) throw new Error("An edit reason of at least 3 characters is required");
      if (!lines.length) throw new Error("A completed invoice cannot be empty. Use Void Invoice to cancel the entire sale.");
      if (Number(selectedDiscount) > subtotal) throw new Error("Discount cannot exceed subtotal");
      return api.patch<Sale>(`/sales/${saleId}`, { customer_name: selectedCustomer.trim() || null, payment_mode: selectedPayment, discount: Number(selectedDiscount) || 0, edit_reason: reason.trim(), version: sale.version, items: lines.map((line) => ({ product_id: line.product.id, quantity: line.quantity, unit_price: line.unitPrice })) });
    },
    onSuccess: (updated) => { setInlineError(""); toast.success(`Invoice ${updated.invoice_number} updated`); void queryClient.invalidateQueries({ queryKey: ["sales-history"] }); void queryClient.invalidateQueries({ queryKey: ["sales-dashboard"] }); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); void queryClient.invalidateQueries({ queryKey: ["sale", saleId] }); navigate("/sales/history"); },
    onError: (error) => { const message = error instanceof ApiError && error.status === 409 ? "This invoice was changed by another user. Reload it before saving." : error instanceof Error ? error.message : "Unable to update sale"; setInlineError(message); toast.error(message); },
  });
  const voidMutation = useMutation({
    mutationFn: () => { if (!saleId || !sale) throw new Error("Sale is unavailable"); if (voidReason.trim().length < 3) throw new Error("A void reason of at least 3 characters is required"); return api.post<Sale>(`/sales/${saleId}/void`, { reason: voidReason.trim(), version: sale.version }); },
    onSuccess: (updated) => { toast.success(`Invoice ${updated.invoice_number} voided and stock restored`); setVoidOpen(false); void queryClient.invalidateQueries({ queryKey: ["sales-history"] }); void queryClient.invalidateQueries({ queryKey: ["sales-dashboard"] }); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); navigate("/sales/history"); },
    onError: (error) => { const message = error instanceof Error ? error.message : "Unable to void invoice"; setInlineError(message); toast.error(message); },
  });

  if (saleQuery.isLoading) return <SkeletonRows rows={7} />;
  if (saleQuery.error || !sale) return <ErrorState message={saleQuery.error instanceof Error ? saleQuery.error.message : "Sale not found"} />;
  return <form onSubmit={(event: FormEvent) => { event.preventDefault(); mutation.mutate(); }}>
    <PageHeader title={`Edit ${sale.invoice_number}`} subtitle={`Original total ${money(sale.total_amount)}`} actions={<Button asChild variant="secondary"><Link to="/sales/history"><ArrowLeft size={16} /> Back to history</Link></Button>} />
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="space-y-4"><label className="flex h-12 items-center rounded-lg border border-line bg-white px-3"><Search size={18} className="text-slate-400" /><input className="min-w-0 flex-1 border-0 px-3 outline-none" placeholder="Add a product" value={search} onChange={(event) => setSearch(event.target.value)} /></label>{productsQuery.isLoading ? <SkeletonRows rows={3} /> : <div className="grid gap-2 sm:grid-cols-2">{(productsQuery.data ?? []).map((product) => <button key={product.id} type="button" onClick={() => addProduct(product)} className="rounded-lg border border-line bg-white p-3 text-left text-sm shadow-sm hover:border-primary"><strong className="block truncate">{product.name}</strong><span className="text-muted">{money(product.selling_price)} · {product.current_stock} available</span></button>)}</div>}<div className="overflow-hidden rounded-lg border border-line bg-white"><div className="divide-y divide-line">{lines.map((line) => { const change = line.quantity - (originalQuantities.get(line.product.id) ?? 0); return <div key={line.product.id} className="flex items-center gap-3 p-4"><div className="min-w-0 flex-1"><strong className="block truncate">{line.product.name}</strong><span className={change === 0 ? "text-xs text-muted" : `text-xs ${change > 0 ? "text-error" : "text-success"}`}>{change === 0 ? "No stock change" : change > 0 ? `${change} more units removed` : `${Math.abs(change)} units restored`}</span></div><div className="flex items-center rounded-lg border border-line"><button type="button" className="grid h-9 w-9 place-items-center" onClick={() => changeQuantity(line.product.id, -1)}><Minus size={15} /></button><span className="w-8 text-center font-semibold">{line.quantity}</span><button type="button" className="grid h-9 w-9 place-items-center" onClick={() => changeQuantity(line.product.id, 1)}><Plus size={15} /></button></div><strong className="w-20 text-right">{money(line.unitPrice * line.quantity)}</strong><button type="button" onClick={() => updateLines((current) => current.filter((item) => item.product.id !== line.product.id))} aria-label={`Remove ${line.product.name}`} className="text-error"><Trash2 size={17} /></button></div>; })}</div>{!lines.length ? <div className="p-4"><EmptyState icon={Trash2} title="Invoice has no items" description="A completed invoice cannot be empty. Use Void Invoice to cancel the entire sale." />{canVoid ? <Button type="button" variant="destructive" className="mx-auto flex" onClick={() => setVoidOpen(true)}><XCircle size={17} /> Void entire invoice</Button> : null}</div> : null}</div></section>
      <aside className="ds-surface h-fit space-y-4 p-5 xl:sticky xl:top-20"><label className="field-label">Customer<input className="field-input" value={selectedCustomer} onChange={(event) => { setCart(lines); setCustomerName(event.target.value); }} placeholder="Walk-in customer" /></label><label className="field-label">Payment method<select className="field-input" value={selectedPayment} onChange={(event) => { setCart(lines); setPaymentMode(event.target.value); }}>{["CASH", "UPI", "CARD", "BANK", "OTHER"].map((mode) => <option key={mode}>{mode}</option>)}</select></label><label className="field-label">Discount<input className="field-input" type="number" min="0" max={subtotal} value={selectedDiscount} onChange={(event) => { setCart(lines); setDiscount(event.target.value); }} /></label><label className="field-label">Edit reason<input required minLength={3} className="field-input" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why is this invoice changing?" /></label>{inlineError ? <ErrorState message={inlineError} /> : null}<div className="space-y-2 border-t border-line pt-4 text-sm"><div className="flex justify-between"><span>Original total</span><strong>{money(sale.total_amount)}</strong></div><div className="flex justify-between text-lg"><span>Updated total</span><strong>{money(total)}</strong></div></div><Button type="submit" className="w-full" disabled={!lines.length || mutation.isPending}><Save size={17} /> {mutation.isPending ? "Saving changes" : "Save sale changes"}</Button></aside>
    </div>
    <ConfirmDialog open={voidOpen} title="Void entire invoice?" description="This restores all remaining items to stock and keeps the invoice for audit history." confirmLabel="Void invoice" loading={voidMutation.isPending} onCancel={() => setVoidOpen(false)} onConfirm={() => voidMutation.mutate()}><label className="field-label">Void reason<input autoFocus required minLength={3} className="field-input mt-2" value={voidReason} onChange={(event) => setVoidReason(event.target.value)} placeholder="Why is this invoice being voided?" /></label></ConfirmDialog>
  </form>;
}

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, FileText, MoreHorizontal, Plus, Printer, Search, ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Dialog from "../components/Dialog";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { PaginatedSales, Sale, SaleReturn } from "../types";
import { money, shortDate } from "../utils/format";

function downloadBlob(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click(); URL.revokeObjectURL(url); }

export default function SalesHistoryPage() {
  const toast = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [cashierName, setCashierName] = useState("");
  const [paymentMode, setPaymentMode] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selected, setSelected] = useState<Sale | null>(null);
  const [actionSale, setActionSale] = useState<Sale | null>(null);
  const [voidSale, setVoidSale] = useState<Sale | null>(null);
  const [returnSale, setReturnSale] = useState<Sale | null>(null);
  const [returnReason, setReturnReason] = useState("");
  const [returnQuantities, setReturnQuantities] = useState<Record<string, number>>({});
  const params = useMemo(() => { const value = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (invoiceNumber.trim()) value.set("invoice_number", invoiceNumber.trim()); if (customerName.trim()) value.set("customer_name", customerName.trim()); if (cashierName.trim()) value.set("cashier_name", cashierName.trim()); if (paymentMode) value.set("payment_mode", paymentMode); if (startDate) value.set("start_date", startDate); if (endDate) value.set("end_date", endDate); return value; }, [cashierName, customerName, endDate, invoiceNumber, page, pageSize, paymentMode, startDate]);
  const query = useQuery({ queryKey: ["sales-history", params.toString()], queryFn: () => api.get<PaginatedSales>(`/sales?${params}`) });
  const sales = query.data?.items ?? [];
  const meta = query.data?.meta;
  const canManage = user?.role === "OWNER" || user?.role === "MANAGER";
  const refresh = () => { void queryClient.invalidateQueries({ queryKey: ["sales-history"] }); void queryClient.invalidateQueries({ queryKey: ["sales-dashboard"] }); void queryClient.invalidateQueries({ queryKey: ["stock-history"] }); };
  const voidMutation = useMutation({ mutationFn: (sale: Sale) => api.post<Sale>(`/sales/${sale.id}/void`, { reason: "Void sale from sales history", version: sale.version }), onSuccess: () => { toast.success("Sale voided and stock restored"); setVoidSale(null); refresh(); }, onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to void sale") });
  const returnMutation = useMutation({ mutationFn: () => { if (!returnSale) throw new Error("Sale is unavailable"); if (returnReason.trim().length < 3) throw new Error("Return reason is required"); const items = returnSale.items.filter((item) => (returnQuantities[item.id] ?? 0) > 0).map((item) => ({ sale_item_id: item.id, quantity: returnQuantities[item.id] })); if (!items.length) throw new Error("Select at least one item quantity"); return api.post<SaleReturn>(`/sales/${returnSale.id}/returns`, { reason: returnReason.trim(), items }); }, onSuccess: () => { toast.success("Customer return recorded"); setReturnSale(null); setReturnReason(""); setReturnQuantities({}); refresh(); }, onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to record return") });

  async function exportSales(format: "xlsx" | "pdf") { try { const exportParams = new URLSearchParams(params); exportParams.delete("page"); exportParams.delete("page_size"); exportParams.set("format", format); downloadBlob(await api.getBlob(`/sales/export?${exportParams}`), `sales-history.${format}`); toast.success(`${format.toUpperCase()} export downloaded`); } catch (error) { toast.error(error instanceof Error ? error.message : "Export failed"); } }
  function printInvoice() { window.print(); }

  return (
    <>
      <PageHeader title="Sales History" subtitle={`${meta?.total_records ?? 0} completed invoices`} actions={<div className="flex flex-wrap gap-2"><Button asChild size="sm"><Link to="/sales"><Plus size={16} /> New Sale</Link></Button><Button type="button" size="sm" variant="secondary" onClick={() => void exportSales("xlsx")}><Download size={15} /> Excel</Button><Button type="button" size="sm" variant="secondary" onClick={() => void exportSales("pdf")}><FileText size={15} /> PDF</Button></div>} />
      <div className="mb-5 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-3">
        <label className="flex h-11 items-center rounded-lg border border-slate-200 px-3"><Search size={16} className="text-slate-400" /><input aria-label="Invoice number" className="min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Invoice number" value={invoiceNumber} onChange={(event) => { setInvoiceNumber(event.target.value); setPage(1); }} /></label>
        <label className="flex h-11 items-center rounded-lg border border-slate-200 px-3"><Search size={16} className="text-slate-400" /><input aria-label="Customer name" className="min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Customer name" value={customerName} onChange={(event) => { setCustomerName(event.target.value); setPage(1); }} /></label>
        <label className="flex h-11 items-center rounded-lg border border-slate-200 px-3"><Search size={16} className="text-slate-400" /><input aria-label="Cashier name" className="min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Cashier name" value={cashierName} onChange={(event) => { setCashierName(event.target.value); setPage(1); }} /></label>
        <select aria-label="Payment mode" className="focus-ring h-10 rounded-md border border-line px-3" value={paymentMode} onChange={(event) => { setPaymentMode(event.target.value); setPage(1); }}><option value="">All payments</option>{["CASH","CARD","UPI","BANK","OTHER"].map((mode) => <option key={mode}>{mode}</option>)}</select>
        <input aria-label="Sales start date" className="focus-ring h-10 rounded-md border border-line px-3" type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPage(1); }} />
        <input aria-label="Sales end date" className="focus-ring h-10 rounded-md border border-line px-3" type="date" min={startDate} value={endDate} onChange={(event) => { setEndDate(event.target.value); setPage(1); }} />
      </div>
      {query.isLoading ? <SkeletonRows rows={7} /> : query.error ? <ErrorState message={query.error instanceof Error ? query.error.message : "Unable to load sales history"} /> : sales.length ? (
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <div className="divide-y divide-line md:hidden">{sales.map((sale) => <button key={sale.id} type="button" className="w-full p-4 text-left hover:bg-slate-50" onClick={() => setSelected(sale)}><div className="flex justify-between gap-3"><div><div className="font-semibold">{sale.invoice_number}</div><div className="mt-1 text-xs text-slate-500">{sale.customer_name || "Walk-in"} · {sale.cashier?.full_name || "-"}</div></div><div className="text-right"><div className="font-semibold">{money(sale.total_amount)}</div><div className="text-xs text-slate-500">{shortDate(sale.sale_date)}</div></div></div></button>)}</div>
          <div className="hidden overflow-x-auto md:block"><table className="min-w-[950px] divide-y divide-line text-sm"><thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Invoice</th><th className="px-4 py-3">Date</th><th className="px-4 py-3">Customer</th><th className="px-4 py-3">Items</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Total</th><th /></tr></thead><tbody className="divide-y divide-line">{sales.map((sale) => <tr key={sale.id}><td className="px-4 py-3 font-medium"><button onClick={() => setSelected(sale)} className="text-primary hover:underline">{sale.invoice_number}</button></td><td className="px-4 py-3 text-slate-600">{shortDate(sale.sale_date)}</td><td className="px-4 py-3">{sale.customer_name || "Walk-in"}</td><td className="px-4 py-3">{sale.items.reduce((total, item) => total + item.quantity, 0)}</td><td className="px-4 py-3"><StatusBadge value={sale.status} /></td><td className="px-4 py-3 text-right font-semibold">{money(sale.total_amount)}</td><td className="px-4 py-3 text-right"><Button type="button" size="icon" variant="ghost" onClick={() => setActionSale(sale)} aria-label={`Actions for ${sale.invoice_number}`}><MoreHorizontal size={18} /></Button></td></tr>)}</tbody></table></div>
          <div className="flex flex-col gap-2 border-t border-line p-3 sm:flex-row sm:items-center sm:justify-between"><span className="text-sm text-slate-500">{meta?.total_records ?? 0} records</span><div className="flex items-center gap-2"><select className="focus-ring h-9 rounded-md border border-line px-2 text-sm" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }}>{[10,25,50,100].map((size) => <option key={size} value={size}>{size} / page</option>)}</select><Button type="button" variant="secondary" size="icon" disabled={!meta || meta.page <= 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={16} /></Button><span className="text-sm">{meta?.page ?? 1} / {meta?.total_pages ?? 1}</span><Button type="button" variant="secondary" size="icon" disabled={!meta || meta.page >= meta.total_pages} onClick={() => setPage((value) => value + 1)}><ChevronRight size={16} /></Button></div></div>
        </div>
      ) : <div className="rounded-lg border border-slate-200 bg-white py-4 text-center shadow-sm"><EmptyState icon={ShoppingCart} title="No completed sales yet" description="Start a new sale to create the first invoice and update inventory automatically." /><Button asChild><Link to="/sales"><Plus size={17} /> New Sale</Link></Button></div>}

      <Dialog open={Boolean(selected)} title={`Invoice ${selected?.invoice_number ?? ""}`} description={selected ? `${shortDate(selected.sale_date)} · ${selected.payment_mode}` : undefined} onClose={() => setSelected(null)} maxWidth="lg">
        {selected ? <div id="printable-invoice"><div className="mb-5 flex justify-between gap-4 text-sm"><div><div className="font-semibold">Rainbow Fashions</div><div className="text-slate-500">Customer: {selected.customer_name || "Walk-in"}</div></div><div className="text-right"><div>Cashier: {selected.cashier?.full_name || "-"}</div><div className="text-slate-500">{new Date(selected.sale_date).toLocaleString("en-IN")}</div></div></div><div className="overflow-x-auto"><table className="w-full min-w-[480px] divide-y divide-line text-sm"><thead className="bg-slate-50 text-left"><tr><th className="px-3 py-2">Product</th><th className="px-3 py-2 text-right">Qty</th><th className="px-3 py-2 text-right">Price</th><th className="px-3 py-2 text-right">Total</th></tr></thead><tbody className="divide-y divide-line">{selected.items.map((item) => <tr key={item.id}><td className="px-3 py-2">{item.product_name}</td><td className="px-3 py-2 text-right">{item.quantity}</td><td className="px-3 py-2 text-right">{money(item.unit_price)}</td><td className="px-3 py-2 text-right">{money(item.line_total)}</td></tr>)}</tbody></table></div><div className="ml-auto mt-4 grid max-w-xs grid-cols-2 gap-2 text-sm"><span>Subtotal</span><strong className="text-right">{money(selected.subtotal)}</strong><span>Discount</span><strong className="text-right">{money(selected.discount)}</strong><span className="border-t border-line pt-2">Total</span><strong className="border-t border-line pt-2 text-right text-lg">{money(selected.total_amount)}</strong></div><div className="mt-5 flex justify-end print:hidden"><Button type="button" onClick={printInvoice}><Printer size={16} /> Print invoice</Button></div></div> : null}
      </Dialog>
      <Dialog open={Boolean(actionSale)} title={`Actions · ${actionSale?.invoice_number ?? ""}`} onClose={() => setActionSale(null)} maxWidth="md"><div className="grid gap-2"><Button type="button" variant="secondary" onClick={() => { setSelected(actionSale); setActionSale(null); }}>View Invoice</Button>{canManage && actionSale?.status !== "VOIDED" && actionSale?.status !== "RETURNED" ? <Button asChild><Link to={`/sales/${actionSale?.id}/edit`}>Edit Sale</Link></Button> : null}{canManage && actionSale?.status !== "VOIDED" && actionSale?.status !== "RETURNED" ? <Button type="button" variant="secondary" onClick={() => { setReturnSale(actionSale); setActionSale(null); }}>Return / Exchange</Button> : null}<Button type="button" variant="secondary" onClick={() => { setSelected(actionSale); setActionSale(null); setTimeout(printInvoice, 0); }}>Print Invoice</Button>{canManage && actionSale?.status !== "VOIDED" ? <Button type="button" variant="destructive" onClick={() => { setVoidSale(actionSale); setActionSale(null); }}>Void Sale</Button> : null}</div></Dialog>
      <ConfirmDialog open={Boolean(voidSale)} title="Void this sale?" description="This returns all unreturned items to stock and keeps the invoice for audit history." confirmLabel="Void sale" loading={voidMutation.isPending} onCancel={() => setVoidSale(null)} onConfirm={() => voidSale && voidMutation.mutate(voidSale)} />
      <Dialog open={Boolean(returnSale)} title={`Return · ${returnSale?.invoice_number ?? ""}`} description="Select quantities to restore to inventory." onClose={() => setReturnSale(null)} maxWidth="md">{returnSale ? <div className="space-y-3">{returnSale.items.map((item) => <label key={item.id} className="flex items-center justify-between gap-4 rounded-lg border border-line p-3"><span><strong className="block">{item.product_name}</strong><span className="text-xs text-muted">Sold {item.quantity} · {money(item.unit_price)} each</span></span><input className="field-input w-20" type="number" min="0" max={item.quantity} value={returnQuantities[item.id] ?? 0} onChange={(event) => setReturnQuantities((current) => ({ ...current, [item.id]: Math.min(item.quantity, Math.max(0, Number(event.target.value) || 0)) }))} /></label>)}<label className="field-label">Return reason<input required className="field-input" value={returnReason} onChange={(event) => setReturnReason(event.target.value)} /></label><Button className="w-full" onClick={() => returnMutation.mutate()} disabled={returnMutation.isPending}>{returnMutation.isPending ? "Recording return" : "Record return"}</Button></div> : null}</Dialog>
    </>
  );
}

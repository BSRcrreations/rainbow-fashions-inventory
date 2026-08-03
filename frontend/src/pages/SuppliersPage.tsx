import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus, Search, Truck } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Supplier, SupplierDetail } from "../types";
import { money, shortDate } from "../utils/format";

const emptySupplier = { name: "", contact_person: "", phone: "", email: "", gst_number: "", city: "", opening_balance: "0", credit_limit: "" };
const emptyPayment = { amount: "", payment_mode: "BANK", reference: "", notes: "" };

export default function SuppliersPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [supplierForm, setSupplierForm] = useState(emptySupplier);
  const [paymentForm, setPaymentForm] = useState(emptyPayment);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const suppliersQuery = useQuery({ queryKey: ["suppliers", search], queryFn: () => api.get<Supplier[]>(`/suppliers?search=${encodeURIComponent(search)}`) });
  const selectedSupplier = selectedId ?? suppliersQuery.data?.[0]?.id ?? null;
  const detailQuery = useQuery({ queryKey: ["supplier", selectedSupplier], queryFn: () => api.get<SupplierDetail>(`/suppliers/${selectedSupplier}`), enabled: Boolean(selectedSupplier) });
  const totals = useMemo(() => (suppliersQuery.data ?? []).reduce((acc, supplier) => ({ due: acc.due + Number(supplier.balance_due ?? 0), purchases: acc.purchases + Number(supplier.purchase_total ?? 0) }), { due: 0, purchases: 0 }), [suppliersQuery.data]);

  const createMutation = useMutation({
    mutationFn: () => api.post<Supplier>("/suppliers", { ...supplierForm, opening_balance: Number(supplierForm.opening_balance || 0), credit_limit: supplierForm.credit_limit ? Number(supplierForm.credit_limit) : null }),
    onSuccess: (supplier) => {
      toast.success("Supplier saved");
      setSupplierForm(emptySupplier);
      setSelectedId(supplier.id);
      void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save supplier"),
  });

  const paymentMutation = useMutation({
    mutationFn: () => api.post<SupplierDetail>(`/suppliers/${selectedSupplier}/payments`, { ...paymentForm, amount: Number(paymentForm.amount) }),
    onSuccess: () => {
      toast.success("Supplier payment recorded");
      setPaymentForm(emptyPayment);
      void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      void queryClient.invalidateQueries({ queryKey: ["supplier", selectedSupplier] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to record payment"),
  });

  function submitSupplier(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  function submitPayment(event: FormEvent) {
    event.preventDefault();
    if (!selectedSupplier) return;
    paymentMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Suppliers" subtitle="Manage vendors, purchase dues, and supplier payments" actions={<Button form="supplier-form" type="submit"><Plus size={16} /> New supplier</Button>} />
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Purchase total" value={money(totals.purchases)} />
        <SummaryCard label="Supplier balance" value={money(totals.due)} tone={totals.due > 0 ? "warn" : "good"} />
        <SummaryCard label="Active suppliers" value={String((suppliersQuery.data ?? []).filter((item) => item.is_active).length)} />
      </div>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <div className="flex h-12 items-center border-b border-line px-4">
            <Search size={16} className="text-slate-400" />
            <input className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Search supplier, phone, GST" value={search} onChange={(event) => setSearch(event.target.value)} />
          </div>
          {suppliersQuery.isLoading ? <SkeletonRows rows={6} /> : suppliersQuery.error ? <ErrorState message={suppliersQuery.error instanceof Error ? suppliersQuery.error.message : "Unable to load suppliers"} /> : (
            <div className="divide-y divide-line">
              {(suppliersQuery.data ?? []).map((supplier) => (
                <button key={supplier.id} type="button" onClick={() => setSelectedId(supplier.id)} className={`grid w-full gap-3 px-4 py-4 text-left transition hover:bg-slate-50 md:grid-cols-[1fr_150px_150px] ${selectedSupplier === supplier.id ? "bg-teal-50/70" : ""}`}>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 font-semibold text-slate-950"><Truck size={16} /> {supplier.name}</div>
                    <div className="mt-1 text-sm text-slate-500">{supplier.contact_person || supplier.phone || "No contact details"}</div>
                  </div>
                  <div><div className="text-xs text-slate-500">Purchases</div><div className="font-semibold">{money(supplier.purchase_total)}</div></div>
                  <div><div className="text-xs text-slate-500">Balance</div><div className={`font-semibold ${Number(supplier.balance_due) > 0 ? "text-amber-700" : "text-emerald-700"}`}>{money(supplier.balance_due)}</div></div>
                </button>
              ))}
            </div>
          )}
        </div>
        <aside className="space-y-5">
          <form id="supplier-form" onSubmit={submitSupplier} className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold text-slate-950">Add supplier</h2>
            <div className="mt-4 grid gap-3">
              <input required className="form-input" placeholder="Business name" value={supplierForm.name} onChange={(event) => setSupplierForm({ ...supplierForm, name: event.target.value })} />
              <input className="form-input" placeholder="Contact person" value={supplierForm.contact_person} onChange={(event) => setSupplierForm({ ...supplierForm, contact_person: event.target.value })} />
              <input className="form-input" placeholder="Phone" value={supplierForm.phone} onChange={(event) => setSupplierForm({ ...supplierForm, phone: event.target.value })} />
              <input className="form-input" placeholder="Email" type="email" value={supplierForm.email} onChange={(event) => setSupplierForm({ ...supplierForm, email: event.target.value })} />
              <input className="form-input" placeholder="GST number" value={supplierForm.gst_number} onChange={(event) => setSupplierForm({ ...supplierForm, gst_number: event.target.value })} />
              <div className="grid grid-cols-2 gap-3">
                <input className="form-input" placeholder="Opening balance" type="number" min="0" value={supplierForm.opening_balance} onChange={(event) => setSupplierForm({ ...supplierForm, opening_balance: event.target.value })} />
                <input className="form-input" placeholder="Credit limit" type="number" min="0" value={supplierForm.credit_limit} onChange={(event) => setSupplierForm({ ...supplierForm, credit_limit: event.target.value })} />
              </div>
            </div>
          </form>
          {detailQuery.data ? (
            <div className="rounded-md border border-line bg-white p-4">
              <h2 className="text-base font-semibold text-slate-950">{detailQuery.data.name}</h2>
              <div className="mt-1 text-sm text-slate-500">{detailQuery.data.phone || detailQuery.data.email || "No contact details"}</div>
              <form onSubmit={submitPayment} className="mt-4 grid gap-3 border-t border-line pt-4">
                <div className="flex items-center gap-2 text-sm font-semibold"><CreditCard size={16} /> Record payment</div>
                <input required className="form-input" placeholder="Amount" type="number" min="1" value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} />
                <select className="form-input" value={paymentForm.payment_mode} onChange={(event) => setPaymentForm({ ...paymentForm, payment_mode: event.target.value })}><option>BANK</option><option>CASH</option><option>UPI</option><option>CARD</option></select>
                <input className="form-input" placeholder="Reference" value={paymentForm.reference} onChange={(event) => setPaymentForm({ ...paymentForm, reference: event.target.value })} />
                <Button type="submit">Save payment</Button>
              </form>
              <div className="mt-5">
                <div className="mb-2 text-sm font-semibold text-slate-800">Ledger</div>
                <div className="max-h-72 divide-y divide-line overflow-auto rounded-md border border-line">
                  {detailQuery.data.ledger.map((entry) => <div key={`${entry.entry_type}-${entry.id}`} className="px-3 py-2 text-sm"><div className="flex justify-between gap-3"><span className="font-medium">{entry.description}</span><span>{money(entry.balance)}</span></div><div className="text-xs text-slate-500">{shortDate(entry.entry_date)} · {entry.entry_type}</div></div>)}
                </div>
              </div>
            </div>
          ) : null}
        </aside>
      </section>
    </div>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: string; tone?: "warn" | "good" }) {
  const toneClass = tone === "warn" ? "text-amber-700" : tone === "good" ? "text-emerald-700" : "text-slate-950";
  return <div className="rounded-md border border-line bg-white p-4"><div className="text-sm text-slate-500">{label}</div><div className={`mt-1 text-2xl font-bold ${toneClass}`}>{value}</div></div>;
}

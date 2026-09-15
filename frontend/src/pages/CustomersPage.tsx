import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus, Search, UserRound } from "lucide-react";
import { ApiError, api } from "../api/client";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Customer, CustomerDetail } from "../types";
import { money, shortDate } from "../utils/format";

const emptyCustomer = { name: "", phone: "", email: "", city: "", opening_credit: "0", credit_limit: "" };
const emptyPayment = { amount: "", payment_mode: "UPI", reference: "", notes: "" };

export default function CustomersPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [customerForm, setCustomerForm] = useState(emptyCustomer);
  const [paymentForm, setPaymentForm] = useState(emptyPayment);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const customersQuery = useQuery({ queryKey: ["customers", search], queryFn: () => api.get<Customer[]>(`/customers?search=${encodeURIComponent(search)}`) });
  const selectedCustomer = selectedId ?? customersQuery.data?.[0]?.id ?? null;
  const detailQuery = useQuery({ queryKey: ["customer", selectedCustomer], queryFn: () => api.get<CustomerDetail>(`/customers/${selectedCustomer}`), enabled: Boolean(selectedCustomer) });
  const totals = useMemo(() => (customersQuery.data ?? []).reduce((acc, customer) => ({ credit: acc.credit + Number(customer.credit_sales_total ?? 0), due: acc.due + Number(customer.balance_due ?? 0) }), { credit: 0, due: 0 }), [customersQuery.data]);
  const customerListError = customersQuery.error instanceof ApiError ? customersQuery.error : null;

  const createMutation = useMutation({
    mutationFn: () => api.post<Customer>("/customers", { ...customerForm, opening_credit: Number(customerForm.opening_credit || 0), credit_limit: customerForm.credit_limit ? Number(customerForm.credit_limit) : null }),
    onSuccess: (customer) => {
      toast.success("Customer saved");
      setCustomerForm(emptyCustomer);
      setSelectedId(customer.id);
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save customer"),
  });

  const paymentMutation = useMutation({
    mutationFn: () => api.post<CustomerDetail>(`/customers/${selectedCustomer}/payments`, { ...paymentForm, amount: Number(paymentForm.amount) }),
    onSuccess: () => {
      toast.success("Customer payment recorded");
      setPaymentForm(emptyPayment);
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
      void queryClient.invalidateQueries({ queryKey: ["customer", selectedCustomer] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to record payment"),
  });

  function submitCustomer(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  function submitPayment(event: FormEvent) {
    event.preventDefault();
    if (selectedCustomer) paymentMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Customers" subtitle="Track customer profiles, credit sales, balances, and collections" actions={<Button form="customer-form" type="submit"><Plus size={16} /> New customer</Button>} />
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Credit sales" value={money(totals.credit)} />
        <SummaryCard label="Customer balance" value={money(totals.due)} tone={totals.due > 0 ? "warn" : "good"} />
        <SummaryCard label="Active customers" value={String((customersQuery.data ?? []).filter((item) => item.is_active).length)} />
      </div>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <div className="flex h-12 items-center border-b border-line px-4">
            <Search size={16} className="text-slate-400" />
            <input className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Search customer, phone, GST" value={search} onChange={(event) => setSearch(event.target.value)} />
          </div>
          {customersQuery.isLoading ? <SkeletonRows rows={6} /> : customersQuery.error ? <CustomerListLoadError requestId={customerListError?.requestId} onRetry={() => void customersQuery.refetch()} /> : (
            <div className="divide-y divide-line">
              {(customersQuery.data ?? []).map((customer) => (
                <button key={customer.id} type="button" onClick={() => setSelectedId(customer.id)} className={`grid w-full gap-3 px-4 py-4 text-left transition hover:bg-slate-50 md:grid-cols-[1fr_150px_150px] ${selectedCustomer === customer.id ? "bg-teal-50/70" : ""}`}>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 font-semibold text-slate-950"><UserRound size={16} /> {customer.name}</div>
                    <div className="mt-1 text-sm text-slate-500">{customer.phone || customer.email || "No contact details"}</div>
                  </div>
                  <div><div className="text-xs text-slate-500">Credit sales</div><div className="font-semibold">{money(customer.credit_sales_total)}</div></div>
                  <div><div className="text-xs text-slate-500">Balance</div><div className={`font-semibold ${Number(customer.balance_due) > 0 ? "text-amber-700" : "text-emerald-700"}`}>{money(customer.balance_due)}</div></div>
                </button>
              ))}
            </div>
          )}
        </div>
        <aside className="space-y-5">
          <form id="customer-form" onSubmit={submitCustomer} className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold text-slate-950">Add customer</h2>
            <div className="mt-4 grid gap-3">
              <input required className="form-input" placeholder="Customer name" value={customerForm.name} onChange={(event) => setCustomerForm({ ...customerForm, name: event.target.value })} />
              <input className="form-input" placeholder="Phone" value={customerForm.phone} onChange={(event) => setCustomerForm({ ...customerForm, phone: event.target.value })} />
              <input className="form-input" placeholder="Email" type="email" value={customerForm.email} onChange={(event) => setCustomerForm({ ...customerForm, email: event.target.value })} />
              <input className="form-input" placeholder="City" value={customerForm.city} onChange={(event) => setCustomerForm({ ...customerForm, city: event.target.value })} />
              <div className="grid grid-cols-2 gap-3">
                <input className="form-input" placeholder="Opening credit" type="number" min="0" value={customerForm.opening_credit} onChange={(event) => setCustomerForm({ ...customerForm, opening_credit: event.target.value })} />
                <input className="form-input" placeholder="Credit limit" type="number" min="0" value={customerForm.credit_limit} onChange={(event) => setCustomerForm({ ...customerForm, credit_limit: event.target.value })} />
              </div>
            </div>
          </form>
          {detailQuery.data ? (
            <div className="rounded-md border border-line bg-white p-4">
              <h2 className="text-base font-semibold text-slate-950">{detailQuery.data.name}</h2>
              <div className="mt-1 text-sm text-slate-500">{detailQuery.data.phone || detailQuery.data.email || "No contact details"}</div>
              <form onSubmit={submitPayment} className="mt-4 grid gap-3 border-t border-line pt-4">
                <div className="flex items-center gap-2 text-sm font-semibold"><CreditCard size={16} /> Record collection</div>
                <input required className="form-input" placeholder="Amount" type="number" min="1" value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} />
                <select className="form-input" value={paymentForm.payment_mode} onChange={(event) => setPaymentForm({ ...paymentForm, payment_mode: event.target.value })}><option>UPI</option><option>CASH</option><option>BANK</option><option>CARD</option></select>
                <input className="form-input" placeholder="Reference" value={paymentForm.reference} onChange={(event) => setPaymentForm({ ...paymentForm, reference: event.target.value })} />
                <Button type="submit">Save collection</Button>
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

export function CustomerListLoadError({ requestId, onRetry }: { requestId?: string; onRetry: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm" role="alert">
      <span className="font-medium text-slate-700">Unable to load customers.</span>
      <Button type="button" variant="secondary" size="sm" onClick={onRetry}>Retry</Button>
      {requestId ? <span className="text-xs text-slate-500">Reference: {requestId}</span> : null}
    </div>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: string; tone?: "warn" | "good" }) {
  const toneClass = tone === "warn" ? "text-amber-700" : tone === "good" ? "text-emerald-700" : "text-slate-950";
  return <div className="rounded-md border border-line bg-white p-4"><div className="text-sm text-slate-500">{label}</div><div className={`mt-1 text-2xl font-bold ${toneClass}`}>{value}</div></div>;
}

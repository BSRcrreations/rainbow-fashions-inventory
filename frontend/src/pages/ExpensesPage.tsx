import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ReceiptIndianRupee } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Expense, ExpenseCategory } from "../types";
import { money, shortDate } from "../utils/format";

const today = new Date().toISOString().slice(0, 10);
const emptyExpense = { category_id: "", expense_date: today, title: "", vendor: "", amount: "", payment_mode: "CASH", reference: "", notes: "" };

export default function ExpensesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [expenseForm, setExpenseForm] = useState(emptyExpense);
  const [categoryName, setCategoryName] = useState("");

  const categoriesQuery = useQuery({ queryKey: ["expense-categories"], queryFn: () => api.get<ExpenseCategory[]>("/expenses/categories") });
  const expensesQuery = useQuery({ queryKey: ["expenses"], queryFn: () => api.get<Expense[]>("/expenses") });
  const total = useMemo(() => (expensesQuery.data ?? []).reduce((sum, expense) => sum + Number(expense.amount), 0), [expensesQuery.data]);

  const createCategory = useMutation({
    mutationFn: () => api.post<ExpenseCategory>("/expenses/categories", { name: categoryName }),
    onSuccess: (category) => {
      toast.success("Expense category saved");
      setCategoryName("");
      setExpenseForm((current) => ({ ...current, category_id: category.id }));
      void queryClient.invalidateQueries({ queryKey: ["expense-categories"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save category"),
  });

  const createExpense = useMutation({
    mutationFn: () => api.post<Expense>("/expenses", { ...expenseForm, amount: Number(expenseForm.amount) }),
    onSuccess: () => {
      toast.success("Expense saved");
      setExpenseForm({ ...emptyExpense, category_id: expenseForm.category_id });
      void queryClient.invalidateQueries({ queryKey: ["expenses"] });
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save expense"),
  });

  function submitCategory(event: FormEvent) {
    event.preventDefault();
    createCategory.mutate();
  }

  function submitExpense(event: FormEvent) {
    event.preventDefault();
    createExpense.mutate();
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Expenses" subtitle="Record shop expenses and keep reports accurate" actions={<Button form="expense-form" type="submit"><Plus size={16} /> Save expense</Button>} />
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Expense total" value={money(total)} />
        <SummaryCard label="Categories" value={String(categoriesQuery.data?.length ?? 0)} />
        <SummaryCard label="Entries" value={String(expensesQuery.data?.length ?? 0)} />
      </div>
      <section className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <aside className="space-y-5">
          <form id="expense-form" onSubmit={submitExpense} className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold text-slate-950">New expense</h2>
            <div className="mt-4 grid gap-3">
              <select required className="form-input" value={expenseForm.category_id} onChange={(event) => setExpenseForm({ ...expenseForm, category_id: event.target.value })}>
                <option value="">Select category</option>
                {(categoriesQuery.data ?? []).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select>
              <input required className="form-input" type="date" value={expenseForm.expense_date} onChange={(event) => setExpenseForm({ ...expenseForm, expense_date: event.target.value })} />
              <input required className="form-input" placeholder="Title" value={expenseForm.title} onChange={(event) => setExpenseForm({ ...expenseForm, title: event.target.value })} />
              <input className="form-input" placeholder="Vendor" value={expenseForm.vendor} onChange={(event) => setExpenseForm({ ...expenseForm, vendor: event.target.value })} />
              <input required className="form-input" placeholder="Amount" type="number" min="1" value={expenseForm.amount} onChange={(event) => setExpenseForm({ ...expenseForm, amount: event.target.value })} />
              <select className="form-input" value={expenseForm.payment_mode} onChange={(event) => setExpenseForm({ ...expenseForm, payment_mode: event.target.value })}><option>CASH</option><option>UPI</option><option>BANK</option><option>CARD</option></select>
              <input className="form-input" placeholder="Reference" value={expenseForm.reference} onChange={(event) => setExpenseForm({ ...expenseForm, reference: event.target.value })} />
            </div>
          </form>
          <form onSubmit={submitCategory} className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold text-slate-950">Expense category</h2>
            <div className="mt-4 flex gap-2">
              <input required className="form-input min-w-0 flex-1" placeholder="Category name" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} />
              <Button type="submit" variant="secondary">Add</Button>
            </div>
          </form>
        </aside>
        <div className="overflow-hidden rounded-md border border-line bg-white">
          {expensesQuery.isLoading ? <SkeletonRows rows={6} /> : expensesQuery.error ? <ErrorState message={expensesQuery.error instanceof Error ? expensesQuery.error.message : "Unable to load expenses"} /> : (
            <div className="divide-y divide-line">
              {(expensesQuery.data ?? []).map((expense) => (
                <div key={expense.id} className="grid gap-3 px-4 py-4 md:grid-cols-[1fr_140px_140px]">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 font-semibold text-slate-950"><ReceiptIndianRupee size={16} /> {expense.title}</div>
                    <div className="mt-1 text-sm text-slate-500">{expense.category?.name || "Expense"} · {expense.vendor || "No vendor"}</div>
                  </div>
                  <div><div className="text-xs text-slate-500">Date</div><div className="font-semibold">{shortDate(expense.expense_date)}</div></div>
                  <div><div className="text-xs text-slate-500">Amount</div><div className="font-semibold text-rose-700">{money(expense.amount)}</div></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-line bg-white p-4"><div className="text-sm text-slate-500">{label}</div><div className="mt-1 text-2xl font-bold text-slate-950">{value}</div></div>;
}

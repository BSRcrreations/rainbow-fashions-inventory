const classes: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  REVIEWED: "bg-amber-100 text-amber-800",
  CONFIRMED: "bg-teal-100 text-teal-800",
  CANCELLED: "bg-rose-100 text-rose-800",
  PURCHASE: "bg-teal-100 text-teal-800",
  SALE: "bg-rose-100 text-rose-800",
  CUSTOMER_RETURN: "bg-sky-100 text-sky-800",
  SUPPLIER_RETURN: "bg-violet-100 text-violet-800",
  DAMAGE: "bg-red-100 text-red-800",
  MANUAL_ADJUSTMENT: "bg-amber-100 text-amber-800"
};

const labels: Record<string, string> = {
  PURCHASE: "Purchase",
  SALE: "Sale",
  CUSTOMER_RETURN: "Customer Return",
  SUPPLIER_RETURN: "Supplier Return",
  DAMAGE: "Damage",
  MANUAL_ADJUSTMENT: "Manual Adjustment",
};

export default function StatusBadge({ value }: { value: string }) {
  return <span className={`rounded px-2 py-1 text-xs font-medium ${classes[value] ?? "bg-slate-100 text-slate-700"}`}>{labels[value] ?? value.replace(/_/g, " ")}</span>;
}

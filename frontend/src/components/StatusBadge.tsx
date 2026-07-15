const classes: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  REVIEWED: "bg-amber-100 text-amber-800",
  CONFIRMED: "bg-teal-100 text-teal-800",
  CANCELLED: "bg-rose-100 text-rose-800",
  PURCHASE: "bg-teal-100 text-teal-800",
  SALE: "bg-rose-100 text-rose-800",
  ADJUSTMENT: "bg-amber-100 text-amber-800"
};

export default function StatusBadge({ value }: { value: string }) {
  return <span className={`rounded px-2 py-1 text-xs font-medium ${classes[value] ?? "bg-slate-100 text-slate-700"}`}>{value}</span>;
}

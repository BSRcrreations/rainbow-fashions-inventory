const classes: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  REVIEWED: "bg-amber-50 text-amber-700 border-amber-200",
  CONFIRMED: "bg-teal-50 text-teal-700 border-teal-200",
  CANCELLED: "bg-rose-50 text-rose-700 border-rose-200",
  PURCHASE: "bg-teal-50 text-teal-700 border-teal-200",
  SALE: "bg-rose-50 text-rose-700 border-rose-200",
  ADJUSTMENT: "bg-amber-50 text-amber-700 border-amber-200"
};

export default function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${classes[value] ?? "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {value}
    </span>
  );
}

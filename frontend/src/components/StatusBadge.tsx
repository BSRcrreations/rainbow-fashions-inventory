const classes: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  REVIEWED: "bg-amber-100 text-amber-800",
  CONFIRMED: "bg-teal-100 text-teal-800",
  CANCELLED: "bg-rose-100 text-rose-800",
  PROCESSING: "bg-sky-100 text-sky-800",
  QUEUED: "bg-sky-100 text-sky-800",
  PREPROCESSING: "bg-sky-100 text-sky-800",
  OCR_RUNNING: "bg-sky-100 text-sky-800",
  AI_EXTRACTION: "bg-sky-100 text-sky-800",
  REVIEW_REQUIRED: "bg-amber-100 text-amber-800",
  READY_TO_CONFIRM: "bg-amber-100 text-amber-800",
  FAILED: "bg-red-100 text-red-800",
  PURCHASE: "bg-teal-100 text-teal-800",
  SALE: "bg-rose-100 text-rose-800",
  CUSTOMER_RETURN: "bg-sky-100 text-sky-800",
  SUPPLIER_RETURN: "bg-violet-100 text-violet-800",
  DAMAGE: "bg-red-100 text-red-800",
  MANUAL_ADJUSTMENT: "bg-amber-100 text-amber-800",
  STOCK_RESET_OUT: "bg-red-100 text-red-800",
  SALE_EDIT_RETURN: "bg-sky-100 text-sky-800",
  SALE_EDIT_DECREASE: "bg-orange-100 text-orange-800",
  SALE_VOID: "bg-red-100 text-red-800",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  EDITED: "bg-blue-100 text-blue-800",
  PARTIALLY_RETURNED: "bg-amber-100 text-amber-800",
  RETURNED: "bg-violet-100 text-violet-800",
  VOIDED: "bg-red-100 text-red-800",
};

const labels: Record<string, string> = {
  PURCHASE: "Purchase",
  SALE: "Sale",
  CUSTOMER_RETURN: "Customer Return",
  SUPPLIER_RETURN: "Supplier Return",
  DAMAGE: "Damage",
  MANUAL_ADJUSTMENT: "Manual Adjustment",
  STOCK_RESET_OUT: "Stock reset",
  SALE_EDIT_RETURN: "Sale edit return",
  SALE_EDIT_DECREASE: "Sale edit decrease",
  SALE_VOID: "Sale void",
};

export default function StatusBadge({ value }: { value: string }) {
  return <span className={`rounded px-2 py-1 text-xs font-medium ${classes[value] ?? "bg-slate-100 text-slate-700"}`}>{labels[value] ?? value.replace(/_/g, " ")}</span>;
}

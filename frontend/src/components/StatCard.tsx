import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  tone: "teal" | "rose" | "amber" | "slate";
  icon: LucideIcon;
}

const toneClasses = {
  teal: "bg-gradient-to-br from-teal-50 to-emerald-100 text-teal-800",
  rose: "bg-gradient-to-br from-rose-50 to-red-100 text-red-700",
  amber: "bg-gradient-to-br from-amber-50 to-orange-100 text-amber-800",
  slate: "bg-gradient-to-br from-slate-50 to-slate-200 text-slate-800"
};

export default function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  return (
    <div className="group rounded-lg border border-slate-200/80 bg-white p-5 shadow-[0_4px_18px_rgba(15,23,42,0.05)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_12px_28px_rgba(15,23,42,0.09)] sm:p-6">
      <div className="flex items-center justify-between">
        <div className="text-[15px] font-medium text-slate-500">{label}</div>
        <div className={`grid h-11 w-11 place-items-center rounded-lg transition-transform duration-200 group-hover:scale-105 ${toneClasses[tone]}`}>
          <Icon size={21} />
        </div>
      </div>
      <div className="mt-5 text-3xl font-bold text-slate-950 sm:text-[2rem]">{value}</div>
    </div>
  );
}

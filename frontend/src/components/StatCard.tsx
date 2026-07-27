import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  tone: "teal" | "rose" | "amber" | "slate";
  icon: LucideIcon;
}

const toneClasses = {
  teal: "bg-primary-100 text-primary-800",
  rose: "bg-rose-100 text-error",
  amber: "bg-amber-100 text-warning",
  slate: "bg-slate-100 text-slate-800"
};

export default function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  return (
    <div className="ds-card group p-5 hover:-translate-y-1 sm:p-6">
      <div className="flex items-center justify-between">
        <div className="text-[15px] font-medium text-muted">{label}</div>
        <div className={`grid h-11 w-11 place-items-center rounded-lg transition-transform duration-200 group-hover:scale-105 ${toneClasses[tone]}`}>
          <Icon size={21} />
        </div>
      </div>
      <div className="mt-5 text-3xl font-bold text-foreground sm:text-[2rem]">{value}</div>
    </div>
  );
}

import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  tone: "teal" | "rose" | "amber" | "slate";
  icon: LucideIcon;
}

const toneClasses = {
  teal: "bg-teal-50 text-teal-800",
  rose: "bg-rose-50 text-rose-800",
  amber: "bg-amber-50 text-amber-800",
  slate: "bg-slate-100 text-slate-800"
};

const toneGradients = {
  teal: "from-teal-500 to-teal-700 shadow-teal-500/20",
  rose: "from-rose-500 to-rose-700 shadow-rose-500/20",
  amber: "from-amber-500 to-amber-700 shadow-amber-500/20",
  slate: "from-slate-500 to-slate-700 shadow-slate-500/20"
};

export default function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-slate-500">{label}</div>
        <div className={`grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br text-white shadow-lg ${toneGradients[tone]}`}>
          <Icon size={20} />
        </div>
      </div>
      <div className="mt-3 text-xl font-bold text-slate-950 md:text-2xl">{value}</div>
    </div>
  );
}

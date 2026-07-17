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

export default function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-500">{label}</div>
        <div className={`grid h-9 w-9 place-items-center rounded-md ${toneClasses[tone]}`}>
          <Icon size={18} />
        </div>
      </div>
      <div className="mt-3 text-xl font-semibold text-slate-950 md:text-2xl">{value}</div>
    </div>
  );
}

import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export default function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="grid place-items-center px-4 py-14 text-center">
      <div className="mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-primary-100 to-primary-200 text-primary-700 shadow-sm">
        <Icon size={30} />
      </div>
      <div className="text-base font-bold text-slate-950">{title}</div>
      <div className="mt-1 max-w-xs text-sm font-medium text-slate-500">{description}</div>
    </div>
  );
}

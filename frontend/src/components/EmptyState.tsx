import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export default function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="grid place-items-center px-4 py-12 text-center">
      <div className="mb-4 grid h-16 w-16 place-items-center rounded-full bg-teal-50 text-teal-700">
        <Icon size={30} />
      </div>
      <div className="font-semibold text-slate-950">{title}</div>
      <div className="mt-1 max-w-sm text-sm text-slate-500">{description}</div>
    </div>
  );
}

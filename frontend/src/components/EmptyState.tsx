import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export default function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="ds-empty">
      <div className="mb-4 grid h-16 w-16 place-items-center rounded-full bg-primary-50 text-primary-700">
        <Icon size={30} />
      </div>
      <div className="font-semibold text-foreground">{title}</div>
      <div className="mt-1 max-w-sm text-sm text-muted">{description}</div>
    </div>
  );
}

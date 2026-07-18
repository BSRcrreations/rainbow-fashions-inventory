import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[2rem] font-bold leading-tight text-slate-950 sm:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-2 text-sm text-slate-500 sm:text-base">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}

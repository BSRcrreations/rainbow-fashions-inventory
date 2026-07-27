export default function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="ds-surface p-5 text-sm text-muted">
      {label}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="ds-surface divide-y divide-border overflow-hidden">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center justify-between gap-4 px-5 py-5">
          <div className="min-w-0 flex-1">
            <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
            <div className="mt-2.5 h-3 w-28 animate-pulse rounded bg-slate-100" />
          </div>
          <div className="h-9 w-20 animate-pulse rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

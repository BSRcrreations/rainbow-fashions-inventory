export default function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-line bg-surface p-4 text-sm font-medium text-slate-500 shadow-sm">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-300 border-t-primary-600" />
      {label}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-line rounded-xl border border-line bg-surface">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center justify-between gap-4 px-4 py-4">
          <div className="min-w-0 flex-1">
            <div className="h-4 w-40 animate-pulse rounded-lg bg-slate-200" />
            <div className="mt-2 h-3 w-28 animate-pulse rounded-lg bg-slate-100" />
          </div>
          <div className="h-9 w-20 animate-pulse rounded-lg bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

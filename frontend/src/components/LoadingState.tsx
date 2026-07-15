export default function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4 text-sm text-slate-500">
      {label}
    </div>
  );
}

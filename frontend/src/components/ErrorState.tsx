import { AlertCircle } from "lucide-react";

export default function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 shadow-sm">
      <AlertCircle size={18} className="mt-0.5 shrink-0" />
      <span className="font-medium">{message}</span>
    </div>
  );
}

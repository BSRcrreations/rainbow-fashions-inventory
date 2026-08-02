import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import Dialog from "./Dialog";
import { Button } from "./ui/button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  children?: ReactNode;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Delete",
  loading = false,
  onCancel,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <Dialog open={open} title={title} description={description} onClose={onCancel} maxWidth="md">
      <div className="space-y-5">
        <div className="flex items-start gap-3 rounded-xl border border-amber-100 bg-amber-50/60 p-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-red-50 text-error">
            <AlertTriangle size={18} />
          </div>
          <p className="text-sm text-slate-700">Please review the details before continuing.</p>
        </div>
        {children}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" data-dialog-initial-focus onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={onConfirm} disabled={loading}>
            {loading ? "Working" : confirmLabel}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

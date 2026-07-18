import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "./ui/button";

interface DialogProps {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  maxWidth?: "md" | "lg" | "xl";
}

const widths = {
  md: "max-w-md",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

export default function Dialog({ open, title, description, children, onClose, maxWidth = "lg" }: DialogProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-950/45 p-0 sm:items-center sm:p-4" role="presentation">
      <section
        aria-describedby={description ? "dialog-description" : undefined}
        aria-labelledby="dialog-title"
        aria-modal="true"
        className={`flex max-h-[94vh] w-full flex-col rounded-t-lg border border-line bg-white shadow-2xl sm:rounded-lg ${widths[maxWidth]}`}
        role="dialog"
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-4 py-4 sm:px-6">
          <div>
            <h2 id="dialog-title" className="text-lg font-semibold text-slate-950">{title}</h2>
            {description ? <p id="dialog-description" className="mt-1 text-sm text-slate-500">{description}</p> : null}
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} title="Close dialog" aria-label="Close dialog">
            <X size={18} />
          </Button>
        </header>
        <div className="overflow-y-auto px-4 py-5 sm:px-6">{children}</div>
      </section>
    </div>
  );
}

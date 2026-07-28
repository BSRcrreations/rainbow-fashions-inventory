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
    <div className="ds-dialog-backdrop flex items-end justify-center overflow-y-auto p-2 sm:items-center sm:p-6" role="presentation">
      <section
        aria-describedby={description ? "dialog-description" : undefined}
        aria-labelledby="dialog-title"
        aria-modal="true"
        className={`ds-dialog flex max-h-[calc(100dvh-1rem)] w-full flex-col overflow-hidden sm:max-h-[calc(100dvh-3rem)] ${widths[maxWidth]}`}
        role="dialog"
      >
        <header className="flex items-start justify-between gap-4 border-b border-border px-4 py-4 sm:px-6">
          <div>
            <h2 id="dialog-title" className="text-lg font-semibold text-foreground">{title}</h2>
            {description ? <p id="dialog-description" className="mt-1 text-sm text-muted">{description}</p> : null}
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} title="Close dialog" aria-label="Close dialog">
            <X size={18} />
          </Button>
        </header>
        <div className="min-h-0 overflow-y-auto break-words px-4 py-5 sm:px-6">{children}</div>
      </section>
    </div>
  );
}

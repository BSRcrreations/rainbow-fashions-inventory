import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Button } from "./ui/button";

interface DialogProps {
  open: boolean;
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  maxWidth?: "md" | "lg" | "xl";
  contentClassName?: string;
  fullHeight?: boolean;
  fullScreen?: boolean;
}

const widths = {
  md: "max-w-lg",
  lg: "max-w-3xl",
  xl: "max-w-6xl",
};

let openDialogCount = 0;
let previousBodyOverflow = "";
let previousBodyPaddingRight = "";

function lockPageScroll() {
  if (openDialogCount === 0) {
    previousBodyOverflow = document.body.style.overflow;
    previousBodyPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`;
  }
  openDialogCount += 1;

  return () => {
    openDialogCount = Math.max(0, openDialogCount - 1);
    if (openDialogCount === 0) {
      document.body.style.overflow = previousBodyOverflow;
      document.body.style.paddingRight = previousBodyPaddingRight;
    }
  };
}

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export default function Dialog({ open, title, description, children, onClose, maxWidth = "lg", contentClassName, fullHeight = false, fullScreen = false }: DialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  const openerRef = useRef<HTMLElement | null>(null);

  useEffect(() => { closeRef.current = onClose; }, [onClose]);

  useEffect(() => {
    if (!open) return;
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? []);
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const unlockPageScroll = lockPageScroll();
    const focusTimer = window.requestAnimationFrame(() => {
      const initialFocus = dialogRef.current?.querySelector<HTMLElement>("[data-dialog-initial-focus], input:not([disabled]):not([type='hidden']), select:not([disabled]), textarea:not([disabled])");
      (initialFocus ?? dialogRef.current)?.focus({ preventScroll: true });
    });

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.cancelAnimationFrame(focusTimer);
      unlockPageScroll();
      openerRef.current?.focus({ preventScroll: true });
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className={`ds-dialog-backdrop flex items-end justify-center overflow-y-auto ${fullScreen ? "p-0" : "p-2 sm:items-center sm:p-4"}`} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeRef.current(); }}>
      <section
        ref={dialogRef}
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={`ds-dialog flex w-full flex-col overflow-hidden ${fullScreen ? "h-[100dvh] max-w-none rounded-none" : fullHeight ? "h-[calc(100svh-1rem)] sm:h-[min(88svh,52rem)]" : "max-h-[calc(100svh-1rem)] sm:max-h-[min(88svh,52rem)]"} ${fullScreen ? "" : widths[maxWidth]}`}
        role="dialog"
        tabIndex={-1}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-surface px-4 py-4 sm:px-6">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-foreground">{title}</h2>
            {description ? <p id={descriptionId} className="mt-1 text-sm text-muted">{description}</p> : null}
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} title="Close dialog" aria-label="Close dialog">
            <X size={18} />
          </Button>
        </header>
        <div className={contentClassName ?? "min-h-0 flex-1 overflow-y-auto overscroll-contain break-words px-4 py-5 [scrollbar-gutter:stable] sm:px-6"}>{children}</div>
      </section>
    </div>,
    document.body
  );
}

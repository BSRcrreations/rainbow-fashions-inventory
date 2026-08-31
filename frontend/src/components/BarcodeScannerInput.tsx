import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ScanLine, Volume2, VolumeX } from "lucide-react";
import { Button } from "./ui/button";

export type BarcodeScanStatus = "READY" | "LOOKING_UP" | "FOUND" | "UNKNOWN" | "ERROR";

interface BarcodeScannerInputProps {
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  compact?: boolean;
  onScan: (barcode: string, signal: AbortSignal) => Promise<void>;
  onStatusChange?: (status: BarcodeScanStatus, message?: string) => void;
}

function beep(success: boolean) {
  try {
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = success ? 880 : 180;
    gain.gain.setValueAtTime(0.035, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.09);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(); oscillator.stop(context.currentTime + 0.09);
  } catch { /* Sound is optional; scanning must work without browser audio support. */ }
}

/** Keyboard-wedge scanner input: Enter is authoritative and each newer scan aborts its stale lookup. */
export default function BarcodeScannerInput({
  label = "Barcode scanner", placeholder = "Scan a barcode and press Enter", disabled = false, autoFocus = false, compact = false, onScan, onStatusChange,
}: BarcodeScannerInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const lastValueRef = useRef("");
  const lastScanAtRef = useRef(0);
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<BarcodeScanStatus>("READY");
  const [message, setMessage] = useState("Ready to scan");
  const [soundEnabled, setSoundEnabled] = useState(true);

  useEffect(() => () => controllerRef.current?.abort(), []);
  useEffect(() => { if (autoFocus) window.requestAnimationFrame(() => inputRef.current?.focus()); }, [autoFocus]);

  function report(next: BarcodeScanStatus, nextMessage: string) {
    setStatus(next); setMessage(nextMessage); onStatusChange?.(next, nextMessage);
  }

  async function submit() {
    const barcode = value.replace(/[\r\n]/g, "").trim();
    if (!barcode || disabled || status === "LOOKING_UP") return;
    const now = Date.now();
    // Many scanners send both keydown Enter and a form submit. Suppress that duplicate only.
    if (barcode === lastValueRef.current && now - lastScanAtRef.current < 250) return;
    lastValueRef.current = barcode; lastScanAtRef.current = now;
    if (barcode.length > 40 || (/^\d+$/.test(barcode) && barcode.length > 20)) {
      setValue(""); report("ERROR", "Barcode looks invalid. Please scan again."); if (soundEnabled) beep(false);
      window.requestAnimationFrame(() => inputRef.current?.focus()); return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController(); controllerRef.current = controller;
    setValue(""); report("LOOKING_UP", "Looking up barcode…");
    try {
      await onScan(barcode, controller.signal);
      if (controller.signal.aborted) return;
      report("FOUND", "Product found"); if (soundEnabled) beep(true);
    } catch (cause) {
      if (controller.signal.aborted) return;
      const text = cause instanceof Error ? cause.message : "Barcode could not be processed";
      const unknown = /not found|not registered|not assigned|barcode_not_found/i.test(text);
      report(unknown ? "UNKNOWN" : "ERROR", unknown ? "Barcode available" : text);
      if (soundEnabled) beep(false);
    } finally {
      if (!controller.signal.aborted) window.requestAnimationFrame(() => inputRef.current?.focus());
    }
  }

  function onSubmit(event: FormEvent) { event.preventDefault(); void submit(); }
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) { if (event.key === "Enter") { event.preventDefault(); void submit(); } }
  const colour = status === "READY" ? "text-muted" : status === "LOOKING_UP" ? "text-primary-700" : status === "FOUND" || status === "UNKNOWN" ? "text-success" : "text-danger";

  return <form onSubmit={onSubmit} className={`rounded-xl border border-primary-200 bg-primary-50/60 shadow-sm ${compact ? "p-2" : "p-3"}`} role="search">
    <div className={`flex items-center gap-3 ${compact ? "min-h-10" : ""}`}><div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary-700 text-white"><ScanLine size={19} /></div><label className="min-w-0 flex-1">{compact ? <span className="sr-only">{label}</span> : <span className="text-sm font-semibold text-foreground">{label}</span>}<input ref={inputRef} autoFocus={autoFocus} aria-label={label} className={`${compact ? "w-full" : "mt-1 w-full"} border-0 bg-transparent p-0 text-sm outline-none placeholder:text-slate-400`} placeholder={placeholder} value={value} disabled={disabled || status === "LOOKING_UP"} onChange={(event) => setValue(event.target.value)} onKeyDown={onKeyDown} autoComplete="off" /></label><Button type="submit" size="sm" variant="secondary" disabled={disabled || status === "LOOKING_UP"}>{status === "LOOKING_UP" ? "Looking up" : "Add"}</Button><button type="button" className="text-muted hover:text-foreground" title={soundEnabled ? "Turn scanner sound off" : "Turn scanner sound on"} aria-label={soundEnabled ? "Turn scanner sound off" : "Turn scanner sound on"} onClick={() => setSoundEnabled((current) => !current)}>{soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}</button></div>
    <p className={`${compact ? "mt-1 pl-13" : "mt-2"} text-xs font-semibold ${colour}`} aria-live="polite">{message}</p>
  </form>;
}

import { useEffect, useRef, useState } from "react";
import Dialog from "./Dialog";
import { Button } from "./ui/button";

type Props = { open: boolean; title: string; summary: string; submitLabel: string; loading?: boolean; error?: string; requestId?: string; onClose: () => void; onSubmit: (password: string) => void; onConfigurePassword?: () => void };

export default function DeletePasswordDialog({ open, title, summary, submitLabel, loading = false, error, requestId, onClose, onSubmit, onConfigurePassword }: Props) {
  const [password, setPassword] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (open) inputRef.current?.focus();
      else setPassword("");
    }, 0);
    return () => window.clearTimeout(timer);
  }, [open]);
  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setPassword(""), 0);
    return () => window.clearTimeout(timer);
  }, [error]);
  const close = () => { if (!loading) { setPassword(""); onClose(); } };
  const passwordNotConfigured = error?.includes("Deletion-password protection is not configured.");
  return <Dialog open={open} title={title} description={summary} onClose={close} maxWidth="md"><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (password && !loading) onSubmit(password); }}><label className="field-label">Deletion password<input ref={inputRef} className="field-input mt-1" type="password" autoComplete="off" value={password} onChange={(event) => setPassword(event.target.value)} disabled={loading} /></label>{error ? <div role="alert" className="max-h-40 overflow-y-auto break-words whitespace-pre-wrap rounded-lg border border-error/25 bg-error/5 p-3 text-sm text-error"><div>{error}</div>{passwordNotConfigured && onConfigurePassword ? <button type="button" className="focus-ring mt-2 text-sm font-medium text-error underline" onClick={() => { close(); onConfigurePassword(); }}>Set deletion password</button> : null}{requestId ? <div className="mt-1 text-xs">Reference: {requestId}</div> : null}</div> : null}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={close} disabled={loading}>Cancel</Button><Button type="submit" variant="destructive" disabled={!password || loading}>{loading ? "Deleting" : submitLabel}</Button></div></form></Dialog>;
}

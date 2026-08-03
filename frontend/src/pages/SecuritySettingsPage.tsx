import { useEffect, useState } from "react";
import { DatabaseBackup, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../hooks/useAuth";

type SecurityState = { configured: boolean; require_password_for_sale_delete: boolean; require_password_for_purchase_delete: boolean };
type BackupComponent = { component: string; status: string; available: boolean; details: Record<string, unknown> };
type BackupState = { configured: boolean; components: BackupComponent[] };

function label(component: string) { return component.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function detail(component: BackupComponent) {
  const value = component.details.finished_at ?? component.details.checked_at ?? component.details.message;
  return typeof value === "string" ? value : component.available ? "No timestamp reported" : "No status reported yet";
}

export default function SecuritySettingsPage() {
  const { user } = useAuth();
  const [state, setState] = useState<SecurityState | null>(null); const [backup, setBackup] = useState<BackupState | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (user?.role !== "OWNER") return; Promise.all([api.get<SecurityState>("/security/destructive-actions").then(setState), api.get<BackupState>("/security/backup-status").then(setBackup)]).catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load security settings")); }, [user?.role]);
  if (user?.role !== "OWNER") return <ErrorState message="Only the store owner can manage destructive action security." />;
  return <><PageHeader title="Security" subtitle="Destructive actions and backup health" /><div className="mx-auto grid max-w-2xl gap-6"><section className="ds-surface p-6"><div className="flex items-start gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-100 text-primary-800"><ShieldCheck size={21} /></span><div><h2 className="font-semibold">Delete protection</h2><p className="mt-1 text-sm text-muted">The deletion password is securely managed by the backend environment and is never shown or saved in the browser.</p></div></div>{error ? <div className="mt-5"><ErrorState message={error} /></div> : null}<dl className="mt-6 divide-y divide-border text-sm"><div className="flex justify-between py-3"><dt>Delete sales</dt><dd className="font-semibold">{state?.require_password_for_sale_delete ? "Enabled" : "Disabled"}</dd></div><div className="flex justify-between py-3"><dt>Delete purchases</dt><dd className="font-semibold">{state?.require_password_for_purchase_delete ? "Enabled" : "Disabled"}</dd></div><div className="flex justify-between py-3"><dt>Deletion password</dt><dd className="font-semibold">{state?.configured ? "Configured" : "Not configured"}</dd></div></dl></section><section className="ds-surface p-6"><div className="flex items-start gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-100 text-primary-800"><DatabaseBackup size={21} /></span><div><h2 className="font-semibold">Backup health</h2><p className="mt-1 text-sm text-muted">Read-only status from the server. Backup contents and credentials are never exposed here.</p></div></div>{backup?.configured === false ? <p className="mt-5 text-sm text-amber-700">Backup status mount is not configured.</p> : <dl className="mt-5 divide-y divide-border text-sm">{backup?.components.map((component) => <div className="flex items-start justify-between gap-4 py-3" key={component.component}><dt><div>{label(component.component)}</div><div className="mt-1 text-xs text-muted">{detail(component)}</div></dt><dd className={`font-semibold ${component.status === "success" ? "text-emerald-700" : component.status === "warning" ? "text-amber-700" : component.status === "critical" || component.status === "failed" ? "text-rose-700" : "text-slate-500"}`}>{component.status}</dd></div>)}</dl>}</section></div></>;
}

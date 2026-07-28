import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../hooks/useAuth";

type SecurityState = { configured: boolean; require_password_for_sale_delete: boolean; require_password_for_purchase_delete: boolean };

export default function SecuritySettingsPage() {
  const { user } = useAuth();
  const [state, setState] = useState<SecurityState | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (user?.role !== "OWNER") return; api.get<SecurityState>("/security/destructive-actions").then(setState).catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load security settings")); }, [user?.role]);
  if (user?.role !== "OWNER") return <ErrorState message="Only the store owner can manage destructive action security." />;
  return <><PageHeader title="Security" subtitle="Destructive actions" /><section className="mx-auto max-w-2xl ds-surface p-6"><div className="flex items-start gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-100 text-primary-800"><ShieldCheck size={21} /></span><div><h2 className="font-semibold">Delete protection</h2><p className="mt-1 text-sm text-muted">The deletion password is securely managed by the backend environment and is never shown or saved in the browser.</p></div></div>{error ? <div className="mt-5"><ErrorState message={error} /></div> : null}<dl className="mt-6 divide-y divide-border text-sm"><div className="flex justify-between py-3"><dt>Delete sales</dt><dd className="font-semibold">{state?.require_password_for_sale_delete ? "Enabled" : "Disabled"}</dd></div><div className="flex justify-between py-3"><dt>Delete purchases</dt><dd className="font-semibold">{state?.require_password_for_purchase_delete ? "Enabled" : "Disabled"}</dd></div><div className="flex justify-between py-3"><dt>Deletion password</dt><dd className="font-semibold">{state?.configured ? "Configured" : "Not configured"}</dd></div></dl></section></>;
}

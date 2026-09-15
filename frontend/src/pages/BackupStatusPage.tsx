import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";

type Backup = { health: string; restore_proven: boolean; posting_allowed: boolean; issues: string[]; components: { component: string; status: string; details: Record<string, unknown> }[] };
export default function BackupStatusPage() {
  const query = useQuery({ queryKey: ["backup-status"], queryFn: () => api.get<Backup>("/security/backup-status") });
  return <div className="space-y-5"><PageHeader title="Backup Status" subtitle="A backup is proven only after a successful restore test." actions={<Button variant="secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh Status</Button>} />{query.error ? <ErrorState message={query.error.message} /> : !query.data ? <p role="status">Checking backup health…</p> : <><section className="ds-surface space-y-3 p-6"><h2 className="text-2xl font-bold">{query.data.health}</h2><p>{query.data.restore_proven ? "Restore test proven" : "A successful restore test is still required."}</p><p>{query.data.posting_allowed ? "Backup evidence allows opening-stock posting." : "Resolve the backup issues before posting opening stock."}</p>{query.data.issues?.map((issue) => <p key={issue} className="rounded-lg bg-amber-50 p-3 text-amber-950">{issue}</p>)}</section><section className="ds-surface divide-y divide-border px-5">{query.data.components.map((entry) => <div key={entry.component} className="flex flex-wrap justify-between gap-4 py-4"><div><h3 className="font-semibold">{entry.component.replace(/_/g, " ")}</h3><p className="mt-1">{String(entry.details.finished_at ?? entry.details.checked_at ?? entry.details.message ?? "No completed run reported")}</p></div><strong>{entry.status.toUpperCase()}</strong></div>)}</section></>}</div>;
}

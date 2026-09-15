import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import Dialog from "../components/Dialog";
import { Button } from "../components/ui/button";
import type { User } from "../types";

const roles = [["OWNER", "Owner — all settings and operations"], ["MANAGER", "Manager — daily operations and approvals"], ["CASHIER", "Cashier — billing and customers"], ["STOCK_STAFF", "Stock staff — receiving stock"], ["ACCOUNTANT", "Accountant — purchases, expenses and reports"], ["VIEWER", "Viewer — read only"]];
const blank = { full_name: "", email: "", password: "", role: "CASHIER" };

export default function UsersPage() {
  const client = useQueryClient(); const [form, setForm] = useState(blank); const [editing, setEditing] = useState<User | null>(null); const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [saved, setSaved] = useState(""); const [skip, setSkip] = useState(0);
  const query = useQuery({ queryKey: ["users", skip], queryFn: () => api.get<User[]>(`/users?skip=${skip}&limit=100`) });
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setSaved("");
    try { await api.post("/users", form); setForm(blank); setSaved("User created. Share their login details privately."); await client.invalidateQueries({ queryKey: ["users"] }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create user."); }
    finally { setBusy(false); }
  }
  async function update(event: FormEvent) {
    event.preventDefault(); if (!editing) return; setBusy(true); setError("");
    try { await api.put(`/users/${editing.id}`, { full_name: editing.full_name, role: editing.role, is_active: editing.is_active, reason }); setEditing(null); setReason(""); setSaved("User updated. Their next request uses the new access permissions."); await client.invalidateQueries({ queryKey: ["users"] }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update user."); }
    finally { setBusy(false); }
  }
  return <div className="space-y-6"><PageHeader title="Users & Roles" subtitle="Give each employee their own account and the access they need." />{error && <ErrorState message={error} />}{saved && <p role="status" className="rounded-lg bg-emerald-50 p-4 text-emerald-900">{saved}</p>}<section className="grid gap-6 lg:grid-cols-[minmax(280px,380px)_1fr]"><form className="ds-surface space-y-5 p-5" onSubmit={(event) => void create(event)}><h2 className="text-xl font-bold">Add a user</h2><label className="field-label">Name<input className="field-input" minLength={2} maxLength={120} required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label><label className="field-label">Email<input className="field-input" type="email" required autoComplete="off" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label className="field-label">Password<input className="field-input" type="password" required minLength={12} maxLength={72} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><span className="text-sm font-normal">Use at least 12 characters.</span></label><label className="field-label">Role<select className="field-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>{roles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><Button className="w-full" type="submit" disabled={busy}><UserPlus size={19} />{busy ? "Saving…" : "Create User"}</Button></form><div className="ds-surface p-5"><h2 className="text-xl font-bold">Shop users</h2>{query.error ? <ErrorState message={query.error.message} /> : query.isLoading ? <p>Loading users…</p> : <div className="mt-3 divide-y divide-border">{query.data?.map((user) => <div key={user.id} className="flex flex-wrap items-center justify-between gap-4 py-4"><div><p className="text-lg font-semibold">{user.full_name}</p><p>{user.email}</p><p className="mt-1 font-semibold">{user.role.replace(/_/g, " ")} · {user.is_active ? "Active" : "Disabled"}</p></div><Button variant="secondary" onClick={() => { setEditing({ ...user }); setReason(""); }}>Change access</Button></div>)}</div>}<div className="mt-4 flex justify-end gap-3"><Button variant="secondary" disabled={!skip} onClick={() => setSkip(Math.max(0, skip - 100))}>Previous</Button><Button variant="secondary" disabled={(query.data?.length ?? 0) < 100} onClick={() => setSkip(skip + 100)}>Next</Button></div></div></section>
    <Dialog open={Boolean(editing)} title="Change user access" onClose={() => !busy && setEditing(null)}>{editing && <form onSubmit={(event) => void update(event)} className="space-y-5">{error && <ErrorState message={error} />}<label className="field-label">Name<input className="field-input" required minLength={2} value={editing.full_name} onChange={(e) => setEditing({ ...editing, full_name: e.target.value })} /></label><label className="field-label">Role<select className="field-input" value={editing.role} onChange={(e) => setEditing({ ...editing, role: e.target.value as User["role"] })}>{roles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}{editing.role === "STAFF" && <option value="STAFF">Legacy staff</option>}</select></label><label className="flex min-h-12 items-center gap-3"><input className="h-5 w-5" type="checkbox" checked={editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} />Account is active</label><label className="field-label">Reason for this change<textarea className="field-input" required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} /></label><div className="flex justify-end gap-3"><Button type="button" variant="secondary" disabled={busy} onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={busy}>Save Access</Button></div></form>}</Dialog>
  </div>;
}

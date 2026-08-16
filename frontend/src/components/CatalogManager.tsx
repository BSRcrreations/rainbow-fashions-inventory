import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Edit3, Layers3, Plus, Search, Trash2 } from "lucide-react";
import { api } from "../api/client";
import type { Brand, Category } from "../types";
import ConfirmDialog from "./ConfirmDialog";
import EmptyState from "./EmptyState";
import ErrorState from "./ErrorState";
import { SkeletonRows } from "./LoadingState";
import PageHeader from "./PageHeader";
import { useToast } from "./ToastProvider";
import { Button } from "./ui/button";

type CatalogItem = Category | Brand;
type CatalogKind = "category" | "brand";

interface CatalogManagerProps {
  kind: CatalogKind;
  title: string;
  subtitle: string;
  endpoint: "/categories" | "/brands";
  emptyDescription: string;
}

interface CatalogFormState {
  name: string;
  description: string;
  is_active: boolean;
}

const emptyForm: CatalogFormState = { name: "", description: "", is_active: true };

function formFromItem(item: CatalogItem): CatalogFormState {
  return {
    name: item.name,
    description: item.description ?? "",
    is_active: item.is_active,
  };
}

export default function CatalogManager<T extends CatalogItem>({
  kind,
  title,
  subtitle,
  endpoint,
  emptyDescription,
}: CatalogManagerProps) {
  const toast = useToast();
  const [items, setItems] = useState<T[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<CatalogFormState>(emptyForm);
  const [editing, setEditing] = useState<T | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const noun = kind === "category" ? "category" : "brand";
  const filteredEmpty = useMemo(() => search.trim().length > 0 && items.length === 0, [items.length, search]);

  const load = useCallback(async (query: string) => {
    setError("");
    try {
      const suffix = query.trim() ? `?search=${encodeURIComponent(query.trim())}` : "";
      setItems(await api.get<T[]>(`${endpoint}${suffix}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : `Unable to load ${noun}s`);
    } finally {
      setLoading(false);
    }
  }, [endpoint, noun]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load updates state after the initial external request resolves.
    void load("");
  }, [load]);

  function validateName(value: string) {
    if (!value.trim()) return `${title.slice(0, -1)} name is required`;
    if (value.trim().length < 2) return `${title.slice(0, -1)} name must be at least 2 characters`;
    return "";
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    const validationError = validateName(form.name);
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError("");
    try {
      await api.post<T>(endpoint, {
        name: form.name.trim(),
        description: form.description.trim() || null,
        is_active: form.is_active,
      });
      setForm(emptyForm);
      toast.success(`${title.slice(0, -1)} added`);
      await load(search);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Unable to save ${noun}`;
      setError(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  async function update(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    const validationError = validateName(form.name);
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError("");
    try {
      await api.put<T>(`${endpoint}/${editing.id}`, {
        name: form.name.trim(),
        description: form.description.trim() || null,
        is_active: form.is_active,
      });
      setEditing(null);
      setForm(emptyForm);
      toast.success(`${title.slice(0, -1)} updated`);
      await load(search);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Unable to update ${noun}`;
      setError(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (!deleteTarget) return;
    setDeleting(true);
    setError("");
    try {
      await api.delete(`${endpoint}/${deleteTarget.id}`);
      toast.success(`${title.slice(0, -1)} deleted`);
      setDeleteTarget(null);
      await load(search);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Unable to delete ${noun}`;
      setError(message);
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  function beginEdit(item: T) {
    setEditing(item);
    setForm(formFromItem(item));
    setError("");
  }

  function cancelEdit() {
    setEditing(null);
    setForm(emptyForm);
    setError("");
  }

  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(340px,420px)]">
        <div className="flex h-10 min-w-0 items-center rounded-md border border-line bg-white px-3">
          <Search size={16} className="shrink-0 text-slate-400" />
          <input
            className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void load(search);
            }}
            placeholder={`Search ${noun}s`}
          />
          <Button type="button" variant="secondary" size="sm" onClick={() => void load(search)}>
            Search
          </Button>
        </div>
        <form onSubmit={editing ? update : create} className="grid gap-2 rounded-md border border-line bg-white p-3 sm:grid-cols-[minmax(0,1fr)_auto]">
          <input
            className="focus-ring h-10 min-w-0 rounded-md border border-line px-3"
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            placeholder={`${title.slice(0, -1)} name`}
            disabled={pending}
          />
          <Button type="submit" disabled={pending}>
            <Plus size={16} /> {pending ? "Saving" : editing ? "Update" : "Add"}
          </Button>
          <input
            className="focus-ring h-10 min-w-0 rounded-md border border-line px-3 sm:col-span-2"
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="Description"
            disabled={pending}
          />
          <label className="flex items-center gap-2 text-sm text-slate-600 sm:col-span-2">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
              disabled={pending}
            />
            Active
          </label>
          {editing ? (
            <Button type="button" variant="secondary" className="sm:col-span-2" onClick={cancelEdit} disabled={pending}>
              Cancel edit
            </Button>
          ) : null}
        </form>
      </div>
      {error ? <ErrorState message={error} /> : null}
      <div className="mt-4 overflow-hidden rounded-md border border-line bg-white">
        {loading ? (
          <SkeletonRows rows={6} />
        ) : items.length ? (
          <div className="divide-y divide-line">
            {items.map((item) => (
              <div key={item.id} className="grid gap-3 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-900">{item.name}</div>
                  <div className="mt-1 text-sm text-slate-500">{item.description || (item.is_active ? "Active" : "Inactive")}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-medium ${item.is_active ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-slate-600"}`}>
                    {item.is_active ? "Active" : "Inactive"}
                  </span>
                  <Button type="button" variant="secondary" size="icon" onClick={() => beginEdit(item)} title={`Edit ${noun}`}>
                    <Edit3 size={16} />
                  </Button>
                  <Button type="button" variant="ghost" size="icon" className="text-rose-700 hover:bg-rose-50" onClick={() => setDeleteTarget(item)} title={`Delete ${noun}`}>
                    <Trash2 size={17} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Layers3}
            title={filteredEmpty ? `No matching ${noun}s` : `No ${noun}s yet`}
            description={filteredEmpty ? "Try a different search term." : emptyDescription}
          />
        )}
      </div>
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Delete ${noun}`}
        description={`Delete "${deleteTarget?.name ?? noun}"? This is blocked if products still use it.`}
        loading={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void remove()}
      />
    </>
  );
}

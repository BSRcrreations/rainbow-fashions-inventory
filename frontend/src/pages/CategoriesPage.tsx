import { FormEvent, useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { Category } from "../types";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setCategories(await api.get<Category[]>("/categories"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post<Category>("/categories", { name, is_active: true });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save category");
    }
  }

  async function remove(id: string) {
    await api.delete(`/categories/${id}`);
    await load();
  }

  return (
    <>
      <PageHeader title="Categories" subtitle="Inventory grouping" />
      <form onSubmit={create} className="mb-4 flex max-w-lg gap-2">
        <input className="focus-ring h-10 flex-1 rounded-md border border-line px-3" value={name} onChange={(event) => setName(event.target.value)} placeholder="Category name" required />
        <button className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white">
          <Plus size={16} /> Add
        </button>
      </form>
      {error ? <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
      <div className="overflow-hidden rounded-md border border-line bg-white">
        {categories.map((category) => (
          <div key={category.id} className="flex items-center justify-between border-b border-line px-4 py-3 last:border-0">
            <div>
              <div className="font-medium text-slate-900">{category.name}</div>
              <div className="text-sm text-slate-500">{category.is_active ? "Active" : "Inactive"}</div>
            </div>
            <button className="focus-ring rounded-md p-2 text-rose-700 hover:bg-rose-50" onClick={() => void remove(category.id)} title="Delete category">
              <Trash2 size={17} />
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

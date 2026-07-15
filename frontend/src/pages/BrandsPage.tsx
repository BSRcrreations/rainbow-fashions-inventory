import { FormEvent, useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { Brand } from "../types";

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setBrands(await api.get<Brand[]>("/brands"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post<Brand>("/brands", { name, is_active: true });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save brand");
    }
  }

  async function remove(id: string) {
    await api.delete(`/brands/${id}`);
    await load();
  }

  return (
    <>
      <PageHeader title="Brands" subtitle="Brand master data" />
      <form onSubmit={create} className="mb-4 flex max-w-lg gap-2">
        <input className="focus-ring h-10 flex-1 rounded-md border border-line px-3" value={name} onChange={(event) => setName(event.target.value)} placeholder="Brand name" required />
        <button className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white">
          <Plus size={16} /> Add
        </button>
      </form>
      {error ? <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
      <div className="overflow-hidden rounded-md border border-line bg-white">
        {brands.map((brand) => (
          <div key={brand.id} className="flex items-center justify-between border-b border-line px-4 py-3 last:border-0">
            <div>
              <div className="font-medium text-slate-900">{brand.name}</div>
              <div className="text-sm text-slate-500">{brand.is_active ? "Active" : "Inactive"}</div>
            </div>
            <button className="focus-ring rounded-md p-2 text-rose-700 hover:bg-rose-50" onClick={() => void remove(brand.id)} title="Delete brand">
              <Trash2 size={17} />
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

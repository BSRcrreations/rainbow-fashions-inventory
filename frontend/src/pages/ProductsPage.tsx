import { FormEvent, useEffect, useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { Brand, Category, PricingType, Product } from "../types";
import { money } from "../utils/format";

const emptyForm = {
  category_id: "",
  brand_id: "",
  name: "",
  size: "",
  color: "",
  purchase_price: "",
  selling_price: "",
  pricing_type: "OWN_PRICE" as PricingType,
  mrp: "",
  current_stock: "0",
  minimum_stock: "0",
  barcode: ""
};

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");

  async function load(query = search) {
    const suffix = query ? `?search=${encodeURIComponent(query)}` : "";
    const [productData, categoryData, brandData] = await Promise.all([
      api.get<Product[]>(`/products${suffix}`),
      api.get<Category[]>("/categories"),
      api.get<Brand[]>("/brands")
    ]);
    setProducts(productData);
    setCategories(categoryData);
    setBrands(brandData);
  }

  useEffect(() => {
    void load("");
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post<Product>("/products", {
        ...form,
        purchase_price: Number(form.purchase_price),
        selling_price: Number(form.selling_price),
        mrp: form.mrp ? Number(form.mrp) : null,
        current_stock: Number(form.current_stock),
        minimum_stock: Number(form.minimum_stock),
        barcode: form.barcode || null,
        is_active: true
      });
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save product");
    }
  }

  async function remove(id: string) {
    await api.delete(`/products/${id}`);
    await load();
  }

  return (
    <>
      <PageHeader title="Products" subtitle="Search, variants, prices, and stock" />
      <div className="mb-4 flex max-w-xl gap-2">
        <div className="flex h-10 flex-1 items-center rounded-md border border-line bg-white px-3">
          <Search size={16} className="text-slate-400" />
          <input className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Brand, category, name, color, size, barcode" />
        </div>
        <button className="focus-ring rounded-md bg-slate-900 px-4 text-sm font-semibold text-white" onClick={() => void load(search)}>Search</button>
      </div>

      <form onSubmit={create} className="mb-5 grid gap-3 rounded-md border border-line bg-white p-4 md:grid-cols-2 xl:grid-cols-4">
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })} required>
          <option value="">Category</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.brand_id} onChange={(event) => setForm({ ...form, brand_id: event.target.value })} required>
          <option value="">Brand</option>
          {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Size" value={form.size} onChange={(event) => setForm({ ...form, size: event.target.value })} required />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Color" value={form.color} onChange={(event) => setForm({ ...form, color: event.target.value })} required />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Purchase price" type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => setForm({ ...form, purchase_price: event.target.value })} required />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Selling price" type="number" min="0" step="0.01" value={form.selling_price} onChange={(event) => setForm({ ...form, selling_price: event.target.value })} required />
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.pricing_type} onChange={(event) => setForm({ ...form, pricing_type: event.target.value as PricingType })}>
          <option value="OWN_PRICE">Own price</option>
          <option value="MRP">MRP</option>
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="MRP" type="number" min="0" step="0.01" value={form.mrp} onChange={(event) => setForm({ ...form, mrp: event.target.value })} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Current stock" type="number" min="0" value={form.current_stock} onChange={(event) => setForm({ ...form, current_stock: event.target.value })} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Minimum stock" type="number" min="0" value={form.minimum_stock} onChange={(event) => setForm({ ...form, minimum_stock: event.target.value })} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Barcode" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} />
        <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-semibold text-white xl:col-span-4">
          <Plus size={16} /> Add product
        </button>
      </form>
      {error ? <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
      <div className="overflow-x-auto rounded-md border border-line bg-white">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Variant</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Stock</th>
              <th className="px-4 py-3">Barcode</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {products.map((product) => (
              <tr key={product.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{product.name}</div>
                  <div className="text-slate-500">{product.brand?.name} / {product.category?.name}</div>
                </td>
                <td className="px-4 py-3">{product.size} / {product.color}</td>
                <td className="px-4 py-3">{money(product.selling_price)}</td>
                <td className="px-4 py-3">{product.current_stock}</td>
                <td className="px-4 py-3">{product.barcode ?? "-"}</td>
                <td className="px-4 py-3 text-right">
                  <button className="focus-ring rounded-md p-2 text-rose-700 hover:bg-rose-50" onClick={() => void remove(product.id)} title="Delete product">
                    <Trash2 size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Edit3, ImagePlus, PackageOpen, Plus, Search, Trash2 } from "lucide-react";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import type { Brand, Category, PricingType, Product } from "../types";
import { money } from "../utils/format";

interface ProductFormState {
  category_id: string;
  brand_id: string;
  name: string;
  size: string;
  color: string;
  purchase_price: string;
  selling_price: string;
  pricing_type: PricingType;
  mrp: string;
  current_stock: string;
  minimum_stock: string;
  barcode: string;
  is_active: boolean;
}

const emptyForm: ProductFormState = {
  category_id: "",
  brand_id: "",
  name: "",
  size: "",
  color: "",
  purchase_price: "",
  selling_price: "",
  pricing_type: "OWN_PRICE",
  mrp: "",
  current_stock: "0",
  minimum_stock: "0",
  barcode: "",
  is_active: true,
};

function formFromProduct(product: Product): ProductFormState {
  return {
    category_id: product.category_id,
    brand_id: product.brand_id,
    name: product.name,
    size: product.size,
    color: product.color,
    purchase_price: String(product.purchase_price),
    selling_price: String(product.selling_price),
    pricing_type: product.pricing_type,
    mrp: product.mrp ? String(product.mrp) : "",
    current_stock: String(product.current_stock),
    minimum_stock: String(product.minimum_stock),
    barcode: product.barcode ?? "",
    is_active: product.is_active,
  };
}

function imageSrc(imageUrl?: string | null) {
  if (!imageUrl) return "";
  if (imageUrl.startsWith("http")) return imageUrl;
  return `${window.location.protocol}//${window.location.hostname}:8000${imageUrl}`;
}

export default function ProductsPage() {
  const toast = useToast();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [form, setForm] = useState<ProductFormState>(emptyForm);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [editing, setEditing] = useState<Product | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const hasProducts = products.length > 0;
  const isFiltered = useMemo(
    () => Boolean(search.trim() || categoryFilter || brandFilter || statusFilter !== "all" || lowStockOnly),
    [brandFilter, categoryFilter, lowStockOnly, search, statusFilter]
  );

  function buildQuery(query = search) {
    const params = new URLSearchParams();
    if (query.trim()) params.set("search", query.trim());
    if (categoryFilter) params.set("category_id", categoryFilter);
    if (brandFilter) params.set("brand_id", brandFilter);
    if (statusFilter !== "all") params.set("is_active", String(statusFilter === "active"));
    if (lowStockOnly) params.set("low_stock", "true");
    const queryString = params.toString();
    return queryString ? `?${queryString}` : "";
  }

  async function load(query = search) {
    setError("");
    try {
      const [productData, categoryData, brandData] = await Promise.all([
        api.get<Product[]>(`/products${buildQuery(query)}`),
        api.get<Category[]>("/categories"),
        api.get<Brand[]>("/brands"),
      ]);
      setProducts(productData);
      setCategories(categoryData);
      setBrands(brandData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load products");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load("");
  }, []);

  function validateForm() {
    const requiredFields: Array<[Exclude<keyof ProductFormState, "is_active">, string]> = [
      ["category_id", "Category is required"],
      ["brand_id", "Brand is required"],
      ["name", "Product name is required"],
      ["size", "Size is required"],
      ["color", "Color is required"],
      ["purchase_price", "Cost is required"],
      ["selling_price", "Price is required"],
    ];
    for (const [key, message] of requiredFields) {
      if (!form[key].trim()) return message;
    }
    const purchasePrice = Number(form.purchase_price);
    const sellingPrice = Number(form.selling_price);
    const currentStock = Number(form.current_stock);
    const minimumStock = Number(form.minimum_stock);
    const mrp = form.mrp ? Number(form.mrp) : null;
    if (!Number.isFinite(purchasePrice) || purchasePrice < 0) return "Cost must be zero or greater";
    if (!Number.isFinite(sellingPrice) || sellingPrice < 0) return "Price must be zero or greater";
    if (!Number.isInteger(currentStock) || currentStock < 0) return "Quantity must be a whole number zero or greater";
    if (!Number.isInteger(minimumStock) || minimumStock < 0) return "Minimum stock must be a whole number zero or greater";
    if (form.pricing_type === "MRP" && (mrp === null || !Number.isFinite(mrp) || mrp < 0)) return "MRP is required for MRP pricing";
    return "";
  }

  function payload() {
    return {
      ...form,
      name: form.name.trim(),
      size: form.size.trim(),
      color: form.color.trim(),
      purchase_price: Number(form.purchase_price),
      selling_price: Number(form.selling_price),
      mrp: form.mrp ? Number(form.mrp) : null,
      current_stock: Number(form.current_stock),
      minimum_stock: Number(form.minimum_stock),
      barcode: form.barcode.trim() || null,
      is_active: form.is_active,
    };
  }

  async function uploadImage(productId: string) {
    if (!imageFile) return;
    const body = new FormData();
    body.append("file", imageFile);
    await api.post<Product>(`/products/${productId}/image`, body);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError("");
    try {
      if (editing) {
        const updated = await api.put<Product>(`/products/${editing.id}`, payload());
        await uploadImage(updated.id);
        toast.success("Product updated");
      } else {
        const created = await api.post<Product>("/products", payload());
        await uploadImage(created.id);
        toast.success("Product added");
      }
      setForm(emptyForm);
      setEditing(null);
      setImageFile(null);
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save product";
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
      await api.delete(`/products/${deleteTarget.id}`);
      toast.success("Product deleted");
      setDeleteTarget(null);
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to delete product";
      setError(message);
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  function beginEdit(product: Product) {
    setEditing(product);
    setForm(formFromProduct(product));
    setImageFile(null);
    setError("");
  }

  function cancelEdit() {
    setEditing(null);
    setForm(emptyForm);
    setImageFile(null);
    setError("");
  }

  return (
    <>
      <PageHeader title="Products" subtitle="Search, variants, prices, and stock" />
      <div className="mb-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto]">
        <div className="flex h-10 min-w-0 items-center rounded-md border border-line bg-white px-3">
          <Search size={16} className="shrink-0 text-slate-400" />
          <input
            className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void load(search);
            }}
            placeholder="Brand, category, name, color, size, barcode"
          />
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <select className="focus-ring h-10 rounded-md border border-line bg-white px-3" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <select className="focus-ring h-10 rounded-md border border-line bg-white px-3" value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}>
            <option value="">All brands</option>
            {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
          </select>
          <select className="focus-ring h-10 rounded-md border border-line bg-white px-3" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <label className="flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm text-slate-600">
            <input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} />
            Low stock
          </label>
          <Button type="button" onClick={() => void load(search)}>Apply</Button>
        </div>
      </div>

      <form onSubmit={save} className="mb-5 grid gap-3 rounded-md border border-line bg-white p-4 md:grid-cols-2 xl:grid-cols-4">
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })} disabled={pending}>
          <option value="">Category</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.brand_id} onChange={(event) => setForm({ ...form, brand_id: event.target.value })} disabled={pending}>
          <option value="">Brand</option>
          {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Size" value={form.size} onChange={(event) => setForm({ ...form, size: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Color" value={form.color} onChange={(event) => setForm({ ...form, color: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Cost" type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => setForm({ ...form, purchase_price: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Price" type="number" min="0" step="0.01" value={form.selling_price} onChange={(event) => setForm({ ...form, selling_price: event.target.value })} disabled={pending} />
        <select className="focus-ring h-10 rounded-md border border-line px-3" value={form.pricing_type} onChange={(event) => setForm({ ...form, pricing_type: event.target.value as PricingType })} disabled={pending}>
          <option value="OWN_PRICE">Own price</option>
          <option value="MRP">MRP</option>
        </select>
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="MRP" type="number" min="0" step="0.01" value={form.mrp} onChange={(event) => setForm({ ...form, mrp: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Quantity" type="number" min="0" value={form.current_stock} onChange={(event) => setForm({ ...form, current_stock: event.target.value })} disabled={pending || Boolean(editing)} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Minimum stock" type="number" min="0" value={form.minimum_stock} onChange={(event) => setForm({ ...form, minimum_stock: event.target.value })} disabled={pending} />
        <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Barcode" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} disabled={pending} />
        <label className="flex h-10 items-center gap-2 rounded-md border border-line px-3 text-sm text-slate-600">
          <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} disabled={pending} />
          Active
        </label>
        <label className="focus-ring flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm text-slate-700 hover:bg-slate-50">
          <ImagePlus size={16} />
          {imageFile ? imageFile.name : "Image"}
          <input className="hidden" type="file" accept=".jpg,.jpeg,.png" onChange={(event) => setImageFile(event.target.files?.[0] ?? null)} disabled={pending} />
        </label>
        <div className="grid gap-2 md:grid-cols-2 xl:col-span-4">
          <Button type="submit" disabled={pending}>
            <Plus size={16} /> {pending ? "Saving" : editing ? "Update product" : "Add product"}
          </Button>
          {editing ? <Button type="button" variant="secondary" onClick={cancelEdit} disabled={pending}>Cancel edit</Button> : null}
        </div>
      </form>
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}

      {loading ? (
        <SkeletonRows rows={7} />
      ) : hasProducts ? (
        <div className="overflow-x-auto rounded-md border border-line bg-white">
          <table className="min-w-[920px] divide-y divide-line text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Variant</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Barcode</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {products.map((product) => (
                <tr key={product.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {product.image_url ? <img src={imageSrc(product.image_url)} alt="" className="h-10 w-10 rounded object-cover" /> : <div className="grid h-10 w-10 place-items-center rounded bg-slate-100 text-slate-400"><PackageOpen size={18} /></div>}
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-900">{product.name}</div>
                        <div className="truncate text-slate-500">{product.brand?.name} / {product.category?.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">{product.size} / {product.color}</td>
                  <td className="px-4 py-3">{money(product.selling_price)}</td>
                  <td className="px-4 py-3">{product.current_stock}</td>
                  <td className="px-4 py-3">{product.barcode ?? "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-1 text-xs font-medium ${product.is_active ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-slate-600"}`}>
                      {product.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="secondary" size="icon" onClick={() => beginEdit(product)} title="Edit product">
                        <Edit3 size={16} />
                      </Button>
                      <Button type="button" variant="ghost" size="icon" className="text-rose-700 hover:bg-rose-50" onClick={() => setDeleteTarget(product)} title="Delete product">
                        <Trash2 size={17} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-md border border-line bg-white">
          <EmptyState
            icon={PackageOpen}
            title={isFiltered ? "No matching products" : "No products yet"}
            description={isFiltered ? "Try clearing filters or searching another barcode, brand, category, size, or color." : "Add products with their brand, category, price, stock, barcode, and optional image."}
          />
        </div>
      )}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete product"
        description={`Delete "${deleteTarget?.name ?? "this product"}"? Stock history may prevent deletion if it is referenced.`}
        loading={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void remove()}
      />
    </>
  );
}

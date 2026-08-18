import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Edit3, ImagePlus, Layers3, Plus, Search, Tags, Trash2 } from "lucide-react";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useAuth } from "../hooks/useAuth";
import type { Brand, Category, CategoryHierarchy, SubCategory } from "../types";

type CatalogType = "category" | "subcategory" | "brand";
type CatalogRecord = Category | SubCategory | Brand;

interface EditorState {
  type: CatalogType;
  parentId?: string;
  record?: CatalogRecord;
}

function BrandLogoPreview({ brand, size = "sm" }: { brand: Brand; size?: "sm" | "lg" }) {
  const [failed, setFailed] = useState(false);
  const dimensions = size === "lg" ? "h-12 w-12 rounded-lg text-sm" : "h-7 w-7 rounded-md text-[10px]";
  if (brand.logo_url && !failed) return <img src={brand.logo_url} alt={`${brand.name} logo`} className={`${dimensions} border border-teal-100 bg-white object-contain p-0.5`} onError={() => setFailed(true)} />;
  return <span className={`grid place-items-center bg-teal-50 font-bold text-teal-700 ${dimensions}`}>{brand.name.slice(0, 2).toUpperCase()}</span>;
}

export default function CategoriesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [active, setActive] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<{ type: CatalogType; record: CatalogRecord } | null>(null);
  const [formError, setFormError] = useState("");
  const [logoUploading, setLogoUploading] = useState(false);
  const canManageBrandLogos = user?.role === "OWNER" || user?.role === "MANAGER";
  const canPermanentlyDelete = user?.role === "OWNER";

  const hierarchyQuery = useQuery({
    queryKey: ["category-hierarchy"],
    queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy"),
  });

  const categories = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return hierarchyQuery.data ?? [];
    return (hierarchyQuery.data ?? []).filter((category) =>
      category.name.toLowerCase().includes(query)
      || category.brands.some((brand) => brand.name.toLowerCase().includes(query))
      || category.subcategories.some((subcategory) => subcategory.name.toLowerCase().includes(query)),
    );
  }, [hierarchyQuery.data, search]);

  function openEditor(type: CatalogType, parentId?: string, record?: CatalogRecord) {
    setEditor({ type, parentId, record });
    setName(record?.name ?? "");
    setDescription(record?.description ?? "");
    setActive(record?.is_active ?? true);
    setFormError("");
  }

  function closeEditor() {
    setEditor(null);
    setFormError("");
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editor) return;
      if (name.trim().length < 2) throw new Error("Name must be at least 2 characters");
      const endpoint = editor.type === "category" ? "/categories" : editor.type === "brand" ? "/brands" : "/subcategories";
      const body = {
        name: name.trim(),
        description: description.trim() || null,
        is_active: active,
        ...(editor.type !== "category" ? { category_id: editor.parentId } : {}),
      };
      if (editor.record) await api.put(`${endpoint}/${editor.record.id}`, body);
      else await api.post(endpoint, body);
    },
    onSuccess: () => {
      toast.success(`${editor?.type === "subcategory" ? "Subcategory" : editor?.type ?? "Item"} saved`);
      closeEditor();
      void queryClient.invalidateQueries({ queryKey: ["category-hierarchy"] });
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
      void queryClient.invalidateQueries({ queryKey: ["brands"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to save item";
      setFormError(message);
      toast.error(message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!deleteTarget) return;
      const endpoint = deleteTarget.type === "category" ? "/categories" : deleteTarget.type === "brand" ? "/brands" : "/subcategories";
      await api.delete(`${endpoint}/${deleteTarget.record.id}`);
    },
    onSuccess: () => {
      toast.success("Item deleted");
      setDeleteTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["category-hierarchy"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to delete item"),
  });

  function toggleCategory(id: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function uploadBrandLogo(file: File) {
    if (!editor?.record || editor.type !== "brand") return;
    setLogoUploading(true);
    setFormError("");
    try {
      const body = new FormData();
      body.append("file", file);
      await api.post(`/brands/${editor.record.id}/logo`, body);
      toast.success("Brand logo updated");
      void queryClient.invalidateQueries({ queryKey: ["category-hierarchy"] });
      closeEditor();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to upload brand logo");
    } finally {
      setLogoUploading(false);
    }
  }

  async function deleteBrandLogo() {
    if (!editor?.record || editor.type !== "brand") return;
    setLogoUploading(true);
    try {
      await api.delete(`/brands/${editor.record.id}/logo`);
      toast.success("Brand logo removed");
      void queryClient.invalidateQueries({ queryKey: ["category-hierarchy"] });
      closeEditor();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to remove brand logo");
    } finally {
      setLogoUploading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Product hierarchy"
        subtitle="Manage categories, their subcategories, and available brands"
        actions={<Button type="button" onClick={() => openEditor("category")}><Plus size={16} /> New category</Button>}
      />
      <div className="mb-4 flex h-10 items-center rounded-md border border-line bg-white px-3">
        <Search size={16} className="text-slate-400" />
        <input aria-label="Search product hierarchy" className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none" placeholder="Search categories, subcategories, or brands" value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>

      {hierarchyQuery.isLoading ? <SkeletonRows rows={6} /> : hierarchyQuery.error ? (
        <ErrorState message={hierarchyQuery.error instanceof Error ? hierarchyQuery.error.message : "Unable to load product hierarchy"} />
      ) : categories.length ? (
        <div className="divide-y divide-line overflow-hidden rounded-md border border-line bg-white">
          {categories.map((category) => {
            const isExpanded = expanded.has(category.id) || Boolean(search);
            return (
              <section key={category.id}>
                <div className="flex items-center gap-3 px-4 py-4">
                  <button type="button" className="grid h-8 w-8 place-items-center rounded-md text-slate-500 hover:bg-slate-100" onClick={() => toggleCategory(category.id)} aria-label={`${isExpanded ? "Collapse" : "Expand"} ${category.name}`}>
                    {isExpanded ? <ChevronDown size={17} /> : <ChevronRight size={17} />}
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-slate-950">{category.name}</div>
                    <div className="mt-0.5 text-xs text-slate-500">{category.subcategories.length} subcategories · {category.brands.length} brands</div>
                  </div>
                  <Button type="button" variant="ghost" size="icon" onClick={() => openEditor("category", undefined, category)} title="Edit category"><Edit3 size={16} /></Button>
                  {canPermanentlyDelete ? <Button type="button" variant="ghost" size="icon" className="text-rose-700" onClick={() => setDeleteTarget({ type: "category", record: category })} title="Delete permanently"><Trash2 size={16} /></Button> : null}
                </div>

                {isExpanded ? (
                  <div className="grid gap-6 border-t border-line bg-slate-50/60 px-4 py-5 lg:grid-cols-2 lg:px-14">
                    <div>
                      <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Layers3 size={16} /> Subcategories</div>
                        <Button type="button" variant="secondary" size="sm" onClick={() => openEditor("subcategory", category.id)}><Plus size={14} /> Add</Button>
                      </div>
                      <div className="divide-y divide-line rounded-md border border-line bg-white">
                        {category.subcategories.length ? category.subcategories.map((subcategory) => (
                          <div key={subcategory.id} className="flex items-center gap-2 px-3 py-2.5 text-sm">
                            <span className="min-w-0 flex-1 truncate">{subcategory.name}</span>
                            <Button type="button" variant="ghost" size="icon" onClick={() => openEditor("subcategory", category.id, subcategory)} title="Edit subcategory"><Edit3 size={14} /></Button>
                            {canPermanentlyDelete ? <Button type="button" variant="ghost" size="icon" className="text-rose-700" onClick={() => setDeleteTarget({ type: "subcategory", record: subcategory })} title="Delete permanently"><Trash2 size={14} /></Button> : null}
                          </div>
                        )) : <div className="px-3 py-4 text-sm text-slate-500">No subcategories</div>}
                      </div>
                    </div>

                    <div>
                      <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Tags size={16} /> Brands</div>
                        <Button type="button" variant="secondary" size="sm" onClick={() => openEditor("brand", category.id)}><Plus size={14} /> Add</Button>
                      </div>
                      <div className="divide-y divide-line rounded-md border border-line bg-white">
                        {category.brands.length ? category.brands.map((brand) => (
                          <div key={brand.id} className="flex items-center gap-2 px-3 py-2.5 text-sm">
                            <BrandLogoPreview brand={brand} />
                            <span className="min-w-0 flex-1 truncate">{brand.name}</span>
                            <Button type="button" variant="ghost" size="icon" onClick={() => openEditor("brand", category.id, brand)} title="Edit brand"><Edit3 size={14} /></Button>
                            {canPermanentlyDelete ? <Button type="button" variant="ghost" size="icon" className="text-rose-700" onClick={() => setDeleteTarget({ type: "brand", record: brand })} title="Delete permanently"><Trash2 size={14} /></Button> : null}
                          </div>
                        )) : <div className="px-3 py-4 text-sm text-slate-500">No brands</div>}
                      </div>
                    </div>
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      ) : (
        <div className="rounded-md border border-line bg-white"><EmptyState icon={Layers3} title="No hierarchy found" description={search ? "Try another search." : "Create a category, then add its subcategories and brands."} /></div>
      )}

      <Dialog open={Boolean(editor)} title={`${editor?.record ? "Edit" : "Add"} ${editor?.type === "subcategory" ? "subcategory" : editor?.type ?? "item"}`} onClose={closeEditor} maxWidth="md">
        <form className="grid gap-4" onSubmit={(event: FormEvent) => { event.preventDefault(); saveMutation.mutate(); }}>
          <label className="field-label">Name<span>*</span><input autoFocus className="field-input" value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label className="field-label">Description<textarea className="focus-ring min-h-20 rounded-md border border-line px-3 py-2 font-normal" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          {editor?.type === "brand" && editor.record ? <div className="rounded-lg border border-line bg-slate-50 p-3"><div className="text-sm font-semibold text-slate-800">Brand logo</div><div className="mt-2 flex flex-wrap items-center gap-3">{(editor.record as Brand).logo_url ? <img src={(editor.record as Brand).logo_url ?? ""} alt={`${editor.record.name} logo`} className="h-12 w-12 rounded-lg border border-teal-100 bg-white object-contain p-1" /> : <span className="grid h-12 w-12 rounded-lg bg-teal-50 text-sm font-bold text-teal-700">{editor.record.name.slice(0, 2).toUpperCase()}</span>}{canManageBrandLogos ? <><label className="cursor-pointer rounded-md border border-teal-200 bg-white px-3 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-50"><ImagePlus size={15} className="mr-1 inline" />{logoUploading ? "Uploading..." : "Upload logo"}<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" disabled={logoUploading} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadBrandLogo(file); }} /></label>{(editor.record as Brand).logo_url ? <Button type="button" variant="ghost" size="sm" disabled={logoUploading} className="text-rose-700" onClick={() => void deleteBrandLogo()}>Remove logo</Button> : null}</> : <span className="text-xs text-slate-500">Only managers and owners can change a brand logo.</span>}</div></div> : null}
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Active</label>
          {formError ? <ErrorState message={formError} /> : null}
          <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={closeEditor}>Cancel</Button><Button type="submit" disabled={saveMutation.isPending}>{saveMutation.isPending ? "Saving" : "Save"}</Button></div>
        </form>
      </Dialog>
      <ConfirmDialog open={Boolean(deleteTarget)} title={`Delete ${deleteTarget?.type ?? "item"} permanently`} description={`Delete "${deleteTarget?.record.name ?? "this item"}" permanently? This is allowed only when nothing depends on it.`} loading={deleteMutation.isPending} onCancel={() => setDeleteTarget(null)} onConfirm={() => deleteMutation.mutate()} />
    </>
  );
}

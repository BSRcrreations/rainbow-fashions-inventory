import { ChangeEvent, DragEvent, FormEvent, Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Barcode, ChevronDown, ChevronLeft, ChevronRight, Download, Edit3, FileDown, FileUp, Filter, History, ImagePlus, PackageOpen, Plus, RefreshCw, Search, Trash2, Wand2, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import BarcodeScannerInput from "../components/BarcodeScannerInput";
import BarcodeLabelDialog from "../components/BarcodeLabelDialog";
import VariantManagementDialog from "../components/VariantManagementDialog";
import ProductBarcodeDetailsDialog from "../components/ProductBarcodeDetailsDialog";
import BarcodeLookupDialog from "../components/BarcodeLookupDialog";
import Dialog from "../components/Dialog";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import HighlightText from "../components/HighlightText";
import { SkeletonRows } from "../components/LoadingState";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/ToastProvider";
import { Button } from "../components/ui/button";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useAuth } from "../hooks/useAuth";
import type { CategoryHierarchy, PaginatedProducts, PricingType, Product, ProductVariant, ProductVariantBarcode } from "../types";
import { money } from "../utils/format";
import { productVariantLabel } from "../utils/product";
import { productPayload, productUpdateErrorMessage } from "./productEditLogic";
import type { ProductEditFormState } from "./productEditLogic";

type SortBy = "name" | "sku" | "selling_price" | "purchase_price" | "stock" | "created_at" | "updated_at";
type SortDir = "asc" | "desc";
type StockStatus = "" | "low" | "out" | "in";

interface BulkDeleteBlocked {
  product_id: string;
  product_name: string;
  reason: string;
  code: string;
  references: Record<string, number>;
  request_id: string;
}

interface BulkDeleteCheck {
  deletable: Array<{ product_id: string; product_name: string }>;
  blocked: BulkDeleteBlocked[];
  request_id: string;
}

interface BulkDeleteResult {
  deleted: Array<{ product_id: string; product_name: string }>;
  blocked: BulkDeleteBlocked[];
  request_id: string;
}

const emptyForm: ProductEditFormState = {
  category_id: "",
  subcategory_id: "",
  brand_id: "",
  sku: "",
  name: "",
  has_sizes: false,
  sizes: [],
  has_colors: false,
  colors: [],
  purchase_price: "",
  selling_price: "",
  pricing_type: "OWN_PRICE",
  mrp: "",
  current_stock: "0",
  minimum_stock: "0",
  barcode: "",
  product_date: new Date().toISOString().slice(0, 10),
  description: "",
  hsn_sac: "",
  is_active: true,
  is_test_data: false,
};

function formFromProduct(product: Product): ProductEditFormState {
  const variants = product.variants ?? [];
  const sizes = Array.from(new Set(variants.map((variant) => variant.size).filter((value): value is string => Boolean(value))));
  const colors = Array.from(new Set(variants.map((variant) => variant.color).filter((value): value is string => Boolean(value))));
  if (!sizes.length && product.size) sizes.push(product.size);
  if (!colors.length && product.color) colors.push(product.color);
  return {
    category_id: product.category_id,
    subcategory_id: product.subcategory_id,
    brand_id: product.brand_id,
    sku: product.sku ?? "",
    name: product.name,
    has_sizes: sizes.length > 0,
    sizes,
    has_colors: colors.length > 0,
    colors,
    purchase_price: String(product.purchase_price),
    selling_price: String(product.selling_price),
    pricing_type: product.pricing_type,
    mrp: product.mrp ? String(product.mrp) : "",
    current_stock: String(product.current_stock),
    minimum_stock: String(product.minimum_stock),
    barcode: product.barcode ?? "",
    product_date: product.product_date,
    description: product.description ?? "",
    hsn_sac: product.hsn_sac ?? "",
    is_active: product.is_active,
    is_test_data: product.is_test_data,
  };
}

function imageSrc(imageUrl?: string | null) {
  if (!imageUrl) return "";
  if (imageUrl.startsWith("http")) return imageUrl;
  return `${window.location.protocol}//${window.location.hostname}:8000${imageUrl}`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ProductsPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [stockStatus, setStockStatus] = useState<StockStatus>("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [form, setForm] = useState<ProductEditFormState>(emptyForm);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteCheck, setDeleteCheck] = useState<BulkDeleteCheck | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [purgeConfirmation, setPurgeConfirmation] = useState("");
  const [deleteResult, setDeleteResult] = useState<BulkDeleteResult | null>(null);
  const [printTarget, setPrintTarget] = useState<Product | null>(null);
  const [managedVariant, setManagedVariant] = useState<{ product: Product; variant: ProductVariant } | null>(null);
  const [newBarcode, setNewBarcode] = useState("");
  const [error, setError] = useState("");
  const [barcodeLookupOpen, setBarcodeLookupOpen] = useState(false);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, categoryFilter, brandFilter, statusFilter, stockStatus, minPrice, maxPrice, createdFrom, createdTo, sortBy, sortDir, pageSize]);

  useEffect(() => {
    if (!imageFile) {
      setImagePreview("");
      return;
    }
    const url = URL.createObjectURL(imageFile);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
      if (event.key.toLowerCase() === "n" && !isTyping && !formOpen) {
        event.preventDefault();
        beginCreate();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [formOpen]);

  const productsQueryKey = [
    "products",
    debouncedSearch,
    categoryFilter,
    brandFilter,
    statusFilter,
    stockStatus,
    minPrice,
    maxPrice,
    createdFrom,
    createdTo,
    sortBy,
    sortDir,
    page,
    pageSize,
  ];

  const productsQuery = useQuery({
    queryKey: productsQueryKey,
    queryFn: async () => {
      const params = new URLSearchParams({ paginated: "true", page: String(page), page_size: String(pageSize), sort_by: sortBy, sort_dir: sortDir });
      if (debouncedSearch.trim()) params.set("search", debouncedSearch.trim());
      if (categoryFilter) params.set("category_id", categoryFilter);
      if (brandFilter) params.set("brand_id", brandFilter);
      if (statusFilter !== "all") params.set("is_active", String(statusFilter === "active"));
      if (stockStatus) params.set("stock_status", stockStatus);
      if (minPrice) params.set("min_price", minPrice);
      if (maxPrice) params.set("max_price", maxPrice);
      if (createdFrom) params.set("created_from", createdFrom);
      if (createdTo) params.set("created_to", createdTo);
      return api.get<PaginatedProducts>(`/products?${params.toString()}`);
    },
  });

  const hierarchyQuery = useQuery({ queryKey: ["category-hierarchy"], queryFn: () => api.get<CategoryHierarchy[]>("/categories/hierarchy") });

  const products = productsQuery.data?.items ?? [];
  const meta = productsQuery.data?.meta;
  const categories = useMemo(() => hierarchyQuery.data ?? [], [hierarchyQuery.data]);
  const brands = useMemo(() => categories.flatMap((category) => category.brands), [categories]);
  const selectedCategory = categories.find((category) => category.id === form.category_id);
  const availableSubcategories = selectedCategory?.subcategories.filter((item) => item.is_active) ?? [];
  const availableBrands = selectedCategory?.brands.filter((item) => item.is_active) ?? [];
  const selectedCount = selectedIds.size;
  const canPermanentlyDelete = user?.role === "OWNER";
  const isFiltered = Boolean(debouncedSearch.trim() || categoryFilter || brandFilter || statusFilter !== "all" || stockStatus || minPrice || maxPrice || createdFrom || createdTo);

  function invalidateProducts() {
    void queryClient.invalidateQueries({ queryKey: ["products"] });
    void queryClient.invalidateQueries({ queryKey: ["inventory-products"] });
    void queryClient.invalidateQueries({ queryKey: ["adjustment-products"] });
    void queryClient.invalidateQueries({ queryKey: ["stock-history"] });
  }

  function validateImage(file: File) {
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) return "Only JPG, PNG, and WEBP images are allowed";
    if (file.size > 5 * 1024 * 1024) return "Image must be 5MB or smaller";
    return "";
  }

  async function compressImage(file: File): Promise<File> {
    if (file.size < 1024 * 1024) return file;
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/webp", 0.82));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], `${file.name.replace(/\.[^.]+$/, "")}.webp`, { type: "image/webp" });
  }

  async function chooseImage(file: File | null) {
    if (!file) return;
    const validationError = validateImage(file);
    if (validationError) {
      setError(validationError);
      toast.error(validationError);
      return;
    }
    try {
      setImageFile(await compressImage(file));
    } catch {
      setImageFile(file);
    }
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    void chooseImage(event.dataTransfer.files[0] ?? null);
  }

  function validateForm() {
    const requiredFields: Array<["category_id" | "subcategory_id" | "brand_id" | "name" | "purchase_price" | "selling_price" | "product_date", string]> = [
      ["category_id", "Category is required"],
      ["subcategory_id", "Subcategory is required"],
      ["brand_id", "Brand is required"],
      ["name", "Enter a product name."],
      ["purchase_price", "Cost is required"],
      ["selling_price", "Price is required"],
      ["product_date", "Product date is required"],
    ];
    for (const [key, message] of requiredFields) {
      if (!form[key].trim()) return message;
    }
    const sizes = form.sizes.map((value) => value.trim()).filter(Boolean);
    const colors = form.colors.map((value) => value.trim()).filter(Boolean);
    if (!editing && form.has_sizes && !sizes.length) return "Add at least one size or turn off sizes";
    if (!editing && form.has_colors && !colors.length) return "Add at least one color or turn off colors";
    if (!editing && new Set(sizes.map((value) => value.toLocaleLowerCase())).size !== sizes.length) return "Sizes must be unique";
    if (!editing && new Set(colors.map((value) => value.toLocaleLowerCase())).size !== colors.length) return "Colors must be unique";
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

  function setVariantEnabled(kind: "sizes" | "colors", enabled: boolean) {
    const flag = kind === "sizes" ? "has_sizes" : "has_colors";
    setForm((current) => ({ ...current, [flag]: enabled, [kind]: enabled ? (current[kind].length ? current[kind] : [""]) : [] }));
  }

  function setVariantValue(kind: "sizes" | "colors", index: number, value: string) {
    setForm((current) => ({ ...current, [kind]: current[kind].map((item, itemIndex) => itemIndex === index ? value : item) }));
  }

  function addVariantValue(kind: "sizes" | "colors") {
    setForm((current) => ({ ...current, [kind]: [...current[kind], ""] }));
  }

  function removeVariantValue(kind: "sizes" | "colors", index: number) {
    setForm((current) => ({ ...current, [kind]: current[kind].filter((_, itemIndex) => itemIndex !== index) }));
  }

  const saveMutation = useMutation({
    mutationFn: async ({ print }: { print: boolean }) => {
      void print;
      const validationError = validateForm();
      if (validationError) throw new Error(validationError);
      const payload = productPayload(form, editing);
      const product = editing ? await api.patch<Product>(`/products/${editing.id}`, payload) : await api.post<Product>("/products", payload);
      if (imageFile) {
        const body = new FormData();
        body.append("file", imageFile);
        return api.post<Product>(`/products/${product.id}/image`, body);
      }
      return product;
    },
    onSuccess: (product, variables) => {
      toast.success(editing ? "Product updated" : "Product added");
      setForm(emptyForm);
      setEditing(null);
      setFormOpen(false);
      setImageFile(null);
      setError("");
      invalidateProducts();
      void queryClient.invalidateQueries({ queryKey: ["pos-variant-catalog"] });
      if (variables.print) setPrintTarget(product);
    },
    onError: (err) => {
      const requestId = err instanceof ApiError && err.requestId ? ` (request ${err.requestId})` : "";
      const message = productUpdateErrorMessage(err instanceof ApiError ? err.code : undefined, err instanceof Error ? err.message : undefined) + requestId;
      setError(message);
      toast.error(message);
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: (productId: string) => api.delete(`/products/${productId}/image`),
    onSuccess: () => {
      toast.success("Image deleted");
      invalidateProducts();
      if (editing) setEditing({ ...editing, image_url: null });
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to delete image"),
  });

  function beginEdit(product: Product) {
    setEditing(product);
    setForm(formFromProduct(product));
    setImageFile(null);
    setError("");
    setFormOpen(true);
  }

  function beginCreate() {
    setEditing(null);
    setForm(emptyForm);
    setImageFile(null);
    setError("");
    setFormOpen(true);
  }

  function openStockAdjustmentForProduct(product: Product | null) {
    const variantId = product?.variants?.length === 1 ? product.variants[0].id : "";
    navigate(variantId ? `/stock-adjustment?variant_id=${variantId}` : "/stock-adjustment");
  }

  async function openPermanentDelete(productIds: string[]) {
    if (!canPermanentlyDelete) {
      toast.error("You do not have permission to permanently delete products.");
      return;
    }
    setError("");
    setDeleteCheck(null);
    setDeleteConfirmation("");
    setPurgeConfirmation("");
    setDeleteDialogOpen(true);
    try {
      setDeleteCheck(await api.post<BulkDeleteCheck>("/products/bulk-delete-check", { product_ids: productIds }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to check product dependencies";
      setError(message);
      toast.error(message);
      setDeleteDialogOpen(false);
    }
  }

  async function confirmPermanentDelete() {
    const eligibleIds = deleteCheck?.deletable.map((item) => item.product_id) ?? [];
    if (!eligibleIds.length || deleteConfirmation !== "DELETE") return;
    try {
      const result = await api.post<BulkDeleteResult>("/products/bulk-delete", { product_ids: eligibleIds, confirmation: deleteConfirmation }, { "X-Request-ID": deleteCheck?.request_id ?? "" });
      setDeleteResult({ ...result, blocked: [...(deleteCheck?.blocked ?? []), ...result.blocked] });
      setSelectedIds((current) => {
        const next = new Set(current);
        result.deleted.forEach((item) => next.delete(item.product_id));
        return next;
      });
      setDeleteDialogOpen(false);
      invalidateProducts();
      toast.success(`${result.deleted.length} product${result.deleted.length === 1 ? "" : "s"} permanently deleted`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to permanently delete products";
      setError(message);
      toast.error(message);
    }
  }

  async function purgeSelectedTestProducts() {
    const productIds = Array.from(selectedIds);
    if (!productIds.length || purgeConfirmation !== "PURGE TEST DATA") return;
    try {
      const result = await api.post<BulkDeleteResult>("/products/bulk-purge-test-data", {
        product_ids: productIds,
        confirmation: purgeConfirmation,
        reason: "Removing test products before importing original inventory",
      }, { "X-Request-ID": deleteCheck?.request_id ?? "" });
      setDeleteResult(result);
      setSelectedIds((current) => {
        const next = new Set(current);
        result.deleted.forEach((item) => next.delete(item.product_id));
        return next;
      });
      setDeleteDialogOpen(false);
      invalidateProducts();
      toast.success(`${result.deleted.length} test product${result.deleted.length === 1 ? "" : "s"} purged`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to purge test products";
      setError(message);
      toast.error(message);
    }
  }

  async function deactivateSelected() {
    const productIds = Array.from(selectedIds);
    if (!productIds.length) return;
    try {
      await Promise.all(productIds.map((productId) => api.put(`/products/${productId}`, { is_active: false })));
      setSelectedIds(new Set());
      setStatusFilter("active");
      toast.success(`${productIds.length} product${productIds.length === 1 ? "" : "s"} deactivated`);
      invalidateProducts();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to deactivate selected products";
      setError(message);
      toast.error(message);
    }
  }

  function cancelEdit() {
    setEditing(null);
    setForm(emptyForm);
    setImageFile(null);
    setError("");
    setFormOpen(false);
  }

  async function generateCode(kind: "sku" | "barcode") {
    try {
      const response = await api.get<{ value: string }>(`/products/generate-code?kind=${kind}`);
      setForm((current) => ({ ...current, [kind]: response.value }));
      toast.success(`${kind.toUpperCase()} generated`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Unable to generate ${kind}`);
    }
  }

  async function scanProduct(barcode: string, signal: AbortSignal) {
    try {
      const lookup = await api.get<ProductVariantBarcode>(`/product-variants/by-barcode/${encodeURIComponent(barcode)}`, { signal });
      const product = await api.get<Product>(`/products/${lookup.product_id}`, { signal });
      const variant = product.variants.find((candidate) => candidate.id === lookup.variant_id);
      if (!variant) throw new Error("The barcode resolved, but its variant details could not be loaded.");
      setManagedVariant({ product, variant });
      toast.success(`${product.name} details loaded. Review and Save Changes to update.`);
    } catch (cause) {
      if (cause instanceof ApiError && (cause.status === 404 || cause.code === "BARCODE_NOT_FOUND")) {
        setNewBarcode(barcode);
        toast.success("Barcode is not registered. Add details when you are ready; nothing has been saved.");
        return;
      }
      throw cause;
    }
  }

  async function exportProducts(format: "csv" | "xlsx", selected = false) {
    try {
      const blob = selected
        ? await api.postBlob(`/products/bulk/export?format=${format}`, { product_ids: Array.from(selectedIds) })
        : await api.getBlob(`/products/export?format=${format}`);
      downloadBlob(blob, selected ? `selected-products.${format}` : `products.${format}`);
      toast.success("Export downloaded");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to export products");
    }
  }

  async function downloadTemplate() {
    try {
      downloadBlob(await api.getBlob("/products/import-template"), "product-import-template.csv");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to download template");
    }
  }

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await api.post<{ created: number; updated: number; skipped: number; errors: Array<{ row: string; message: string }> }>("/products/import", body);
      toast.success(`Import complete: ${response.created} created, ${response.updated} updated, ${response.skipped} skipped`);
      if (response.errors.length) setError(response.errors.map((item) => `Row ${item.row}: ${item.message}`).join(" | "));
      invalidateProducts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      event.target.value = "";
    }
  }

  function toggleSelected(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleExpanded(id: string) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function printVariantLabel(product: Product, variant: Product["variants"][number]) {
    setPrintTarget({
      ...product,
      sku: variant.internal_sku,
      barcode: variant.barcode,
      size: variant.size,
      color: variant.color,
      mrp: variant.mrp,
      selling_price: variant.selling_price,
      purchase_price: variant.average_cost || variant.last_purchase_cost || product.purchase_price,
      current_stock: variant.current_stock,
    });
  }

  function toggleAllVisible() {
    setSelectedIds((current) => {
      const visibleIds = products.map((product) => product.id);
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => current.has(id));
      const next = new Set(current);
      visibleIds.forEach((id) => {
        if (allSelected) next.delete(id);
        else next.add(id);
      });
      return next;
    });
  }

  const currentRange = useMemo(() => {
    if (!meta || meta.total_records === 0) return "0 records";
    const start = (meta.page - 1) * meta.page_size + 1;
    const end = Math.min(meta.page * meta.page_size, meta.total_records);
    return `${start}-${end} of ${meta.total_records}`;
  }, [meta]);

  function clearFilters() {
    setSearch("");
    setCategoryFilter("");
    setBrandFilter("");
    setStatusFilter("all");
    setStockStatus("");
    setMinPrice("");
    setMaxPrice("");
    setCreatedFrom("");
    setCreatedTo("");
  }

  return (
    <>
      <PageHeader
        title="Products"
        subtitle={`${meta?.total_records ?? 0} products in your inventory`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={downloadTemplate} title="Download import template"><FileDown size={16} /> Template</Button>
            <label className="focus-ring inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              <FileUp size={16} /> Import original stock
              <input className="hidden" type="file" accept=".csv,.xlsx" onChange={(event) => void importFile(event)} />
            </label>
            {canPermanentlyDelete ? <Button type="button" variant="secondary" size="sm" onClick={() => setBarcodeLookupOpen(true)} title="Find barcode"><Barcode size={16} /> Find Barcode</Button> : null}
            <Button type="button" variant="secondary" size="sm" onClick={() => void exportProducts("xlsx")} title="Export products"><Download size={16} /> Export</Button>
            <Button type="button" size="sm" onClick={beginCreate}><Plus size={16} /> New product</Button>
          </div>
        }
      />

      <div className="sticky top-[65px] z-[5] mb-4 rounded-md border border-line bg-white p-3 shadow-sm">
        <div className="mb-3"><BarcodeScannerInput label="Scan product or variant barcode" placeholder="Scan to load editable details. Nothing is saved until you choose Add Details or Save Changes." onScan={scanProduct} /></div>
        <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:flex">
          <div className="col-span-2 flex h-10 min-w-0 flex-1 items-center rounded-md border border-line bg-white px-3 sm:col-span-1">
          <Search size={16} className="shrink-0 text-slate-400" />
            <input ref={searchInputRef} aria-label="Search products" className="focus-ring min-w-0 flex-1 border-0 px-2 outline-none" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search products, SKU or barcode" />
            {search ? <button type="button" className="text-slate-400 hover:text-slate-700" onClick={() => setSearch("")} title="Clear search"><X size={16} /></button> : <span className="hidden rounded border border-line px-1.5 py-0.5 text-[11px] text-slate-400 sm:inline">/</span>}
          </div>
          <Button type="button" variant="secondary" onClick={() => setFiltersOpen((current) => !current)}>
            <Filter size={16} /> Filters {isFiltered ? <span className="rounded-full bg-teal-100 px-1.5 text-xs text-teal-800">On</span> : null}
          </Button>
          <Button type="button" variant="ghost" size="icon" onClick={() => void productsQuery.refetch()} title="Refresh products"><RefreshCw size={16} /></Button>
        </div>

        {isFiltered ? (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            {categoryFilter ? <button type="button" className="filter-chip" onClick={() => setCategoryFilter("")}>{categories.find((item) => item.id === categoryFilter)?.name}<X size={12} /></button> : null}
            {brandFilter ? <button type="button" className="filter-chip" onClick={() => setBrandFilter("")}>{brands.find((item) => item.id === brandFilter)?.name}<X size={12} /></button> : null}
            {stockStatus ? <button type="button" className="filter-chip" onClick={() => setStockStatus("")}>{stockStatus === "in" ? "In stock" : stockStatus === "low" ? "Low stock" : "Out of stock"}<X size={12} /></button> : null}
            {statusFilter !== "all" ? <button type="button" className="filter-chip" onClick={() => setStatusFilter("all")}>{statusFilter}<X size={12} /></button> : null}
            {minPrice || maxPrice ? <button type="button" className="filter-chip" onClick={() => { setMinPrice(""); setMaxPrice(""); }}>Price {minPrice || "0"}-{maxPrice || "any"}<X size={12} /></button> : null}
            {createdFrom || createdTo ? <button type="button" className="filter-chip" onClick={() => { setCreatedFrom(""); setCreatedTo(""); }}>Date range<X size={12} /></button> : null}
            <button type="button" className="font-medium text-teal-700 hover:text-teal-900" onClick={clearFilters}>Clear all</button>
          </div>
        ) : null}

        {filtersOpen ? <div className="mt-3 grid gap-3 border-t border-line pt-3 sm:grid-cols-2 xl:grid-cols-5">
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}>
            <option value="">All brands</option>
            {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
          </select>
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={stockStatus} onChange={(event) => setStockStatus(event.target.value as StockStatus)}>
            <option value="">All stock</option>
            <option value="in">In stock</option>
            <option value="low">Low stock</option>
            <option value="out">Out of stock</option>
          </select>
          <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Min price" type="number" min="0" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} />
          <input className="focus-ring h-10 rounded-md border border-line px-3" placeholder="Max price" type="number" min="0" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} />
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <input aria-label="Created after" className="focus-ring h-10 rounded-md border border-line px-3" type="date" value={createdFrom} onChange={(event) => setCreatedFrom(event.target.value)} />
          <input aria-label="Created before" className="focus-ring h-10 rounded-md border border-line px-3" type="date" value={createdTo} onChange={(event) => setCreatedTo(event.target.value)} />
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={sortBy} onChange={(event) => setSortBy(event.target.value as SortBy)}>
            <option value="created_at">Recently added</option>
            <option value="updated_at">Recently updated</option>
            <option value="name">Name</option>
            <option value="sku">SKU</option>
            <option value="selling_price">Selling price</option>
            <option value="purchase_price">Cost price</option>
            <option value="stock">Stock</option>
          </select>
          <select className="focus-ring h-10 rounded-md border border-line px-3" value={sortDir} onChange={(event) => setSortDir(event.target.value as SortDir)}>
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
          <Button type="button" variant="secondary" onClick={clearFilters}>Clear filters</Button>
        </div> : null}
      </div>

      <Dialog open={formOpen} title={editing ? "Edit product" : "Add product"} description={editing ? "Changes product information only. Stock quantity is unchanged." : "Add the essentials now. Opening stock is recorded only when the product is created."} onClose={cancelEdit} maxWidth="xl">
      <form onSubmit={(event: FormEvent) => { event.preventDefault(); saveMutation.mutate({ print: false }); }} className="grid gap-4 sm:grid-cols-2">
        {editing ? <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-900 sm:col-span-2">
          <div className="font-semibold">Product editing updates catalogue details only.</div>
          <p className="mt-1">Use this form for product name, category, brand, barcode, price, image, low-stock alert, and active status. Use Stock Adjustment to correct current physical stock.</p>
        </div> : null}
        <label className="field-label">Category<span>*</span>
        <select autoFocus className="field-input" value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value, subcategory_id: "", brand_id: "" })} disabled={saveMutation.isPending}>
          <option value="">Category</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
        </label>
        <label className="field-label">Subcategory<span>*</span>
        <select className="field-input" value={form.subcategory_id} onChange={(event) => setForm({ ...form, subcategory_id: event.target.value })} disabled={saveMutation.isPending || !form.category_id}>
          <option value="">{form.category_id ? "Subcategory" : "Select category first"}</option>
          {availableSubcategories.map((subcategory) => <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>)}
        </select>
        </label>
        <label className="field-label">Brand<span>*</span>
        <select className="field-input" value={form.brand_id} onChange={(event) => setForm({ ...form, brand_id: event.target.value })} disabled={saveMutation.isPending || !form.category_id}>
          <option value="">{form.category_id ? "Brand" : "Select category first"}</option>
          {availableBrands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
        </select>
        </label>
        <label className="field-label sm:col-span-2">Product name<span>*</span>
          <input aria-label="Product name" className="field-input" placeholder="e.g. Cotton leggings" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} disabled={saveMutation.isPending} autoComplete="off" />
        </label>
        <label className="field-label">SKU
        <div className="flex gap-2">
          <input className="field-input min-w-0 flex-1" placeholder="Optional" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} disabled={saveMutation.isPending} />
          <Button type="button" variant="secondary" size="icon" onClick={() => void generateCode("sku")} title="Generate SKU"><Wand2 size={16} /></Button>
        </div>
        </label>
        <label className="field-label">Barcode
        <div className="flex gap-2">
          <input className="field-input min-w-0 flex-1" placeholder="Optional" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} disabled={saveMutation.isPending} />
          <Button type="button" variant="secondary" size="icon" onClick={() => void generateCode("barcode")} title="Generate barcode"><Wand2 size={16} /></Button>
        </div>
        </label>
        <label className="field-label">Product date<span>*</span><input className="field-input" type="date" value={form.product_date} onChange={(event) => setForm({ ...form, product_date: event.target.value })} disabled={saveMutation.isPending} /></label>
        <label className="field-label">HSN / SAC<input className="field-input" placeholder="Optional" value={form.hsn_sac} onChange={(event) => setForm((current) => ({ ...current, hsn_sac: event.target.value }))} disabled={saveMutation.isPending} /></label>
        <label className="field-label sm:col-span-2">Description<textarea className="field-input mt-1 min-h-20" placeholder="Optional product details" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} disabled={saveMutation.isPending} /></label>
        {!editing ? <><div className="grid gap-3 rounded-lg border border-border bg-surface-subtle p-4 sm:col-span-2 sm:grid-cols-2">
          <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border border-border bg-surface px-3 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={form.has_colors} onChange={(event) => setVariantEnabled("colors", event.target.checked)} disabled={saveMutation.isPending} />
            This product has Colors
          </label>
          <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border border-border bg-surface px-3 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={form.has_sizes} onChange={(event) => setVariantEnabled("sizes", event.target.checked)} disabled={saveMutation.isPending} />
            This product has Sizes
          </label>
        </div>
        {form.has_colors ? <div className="space-y-3 rounded-lg border border-border p-4 sm:col-span-2"><div><div className="text-sm font-semibold text-foreground">Colors</div><div className="mt-1 text-xs text-muted">Add every color this product is available in.</div></div>{form.colors.map((color, index) => <div key={`color-${index}`} className="flex gap-2"><input className="field-input min-w-0 flex-1" aria-label={`Color ${index + 1}`} placeholder="e.g. Black" value={color} onChange={(event) => setVariantValue("colors", index, event.target.value)} disabled={saveMutation.isPending} />{form.colors.length > 1 ? <Button type="button" variant="ghost" size="icon" onClick={() => removeVariantValue("colors", index)} aria-label={`Remove color ${index + 1}`}><X size={17} /></Button> : null}</div>)}<Button type="button" variant="secondary" size="sm" onClick={() => addVariantValue("colors")} disabled={saveMutation.isPending}><Plus size={16} /> Add Another</Button></div> : null}
        {form.has_sizes ? <div className="space-y-3 rounded-lg border border-border p-4 sm:col-span-2"><div><div className="text-sm font-semibold text-foreground">Sizes</div><div className="mt-1 text-xs text-muted">Add every size this product is available in.</div></div>{form.sizes.map((size, index) => <div key={`size-${index}`} className="flex gap-2"><input className="field-input min-w-0 flex-1" aria-label={`Size ${index + 1}`} placeholder="e.g. M" value={size} onChange={(event) => setVariantValue("sizes", index, event.target.value)} disabled={saveMutation.isPending} />{form.sizes.length > 1 ? <Button type="button" variant="ghost" size="icon" onClick={() => removeVariantValue("sizes", index)} aria-label={`Remove size ${index + 1}`}><X size={17} /></Button> : null}</div>)}<Button type="button" variant="secondary" size="sm" onClick={() => addVariantValue("sizes")} disabled={saveMutation.isPending}><Plus size={16} /> Add Another</Button></div> : null}</> : <div className="rounded-lg border border-teal-100 bg-teal-50/50 p-3 text-sm text-teal-950 sm:col-span-2">Sizes and colours belong to exact variants. Open a variant’s <strong>Manage</strong> action to correct them.</div>}
        <label className="field-label">Cost price<span>*</span><input className="field-input" placeholder="0.00" type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => setForm({ ...form, purchase_price: event.target.value })} disabled={saveMutation.isPending} /></label>
        <label className="field-label">Selling price<span>*</span><input className="field-input" placeholder="0.00" type="number" min="0" step="0.01" value={form.selling_price} onChange={(event) => setForm({ ...form, selling_price: event.target.value })} disabled={saveMutation.isPending} /></label>
        <label className="field-label">Pricing<select className="field-input" value={form.pricing_type} onChange={(event) => setForm({ ...form, pricing_type: event.target.value as PricingType })} disabled={saveMutation.isPending}>
          <option value="OWN_PRICE">Own price</option>
          <option value="MRP">MRP</option>
        </select></label>
        <label className="field-label">MRP<input className="field-input" placeholder="Optional" type="number" min="0" step="0.01" value={form.mrp} onChange={(event) => setForm({ ...form, mrp: event.target.value })} disabled={saveMutation.isPending} /></label>
        <div className="field-label"><span>{editing ? "Current stock" : "Opening stock"}</span><input className="field-input mt-1" type="number" min="0" value={form.current_stock} onChange={(event) => setForm({ ...form, current_stock: event.target.value })} disabled={saveMutation.isPending || Boolean(editing)} />{editing ? <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-950"><p>Current stock is transaction-controlled and cannot be edited as a product field.</p><Button type="button" variant="secondary" size="sm" className="mt-2" onClick={() => openStockAdjustmentForProduct(editing)}><span>Open Stock Adjustment</span></Button></div> : null}</div>
        <label className="field-label">Low stock alert<input className="field-input" type="number" min="0" value={form.minimum_stock} onChange={(event) => setForm({ ...form, minimum_stock: event.target.value })} disabled={saveMutation.isPending} /></label>
        <label className="flex h-10 items-center gap-2 rounded-md border border-line px-3 text-sm text-slate-600 sm:col-span-2">
          <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} disabled={saveMutation.isPending} />
          Product is active and available for inventory operations
        </label>
        {canPermanentlyDelete ? <label className="flex h-10 items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 text-sm text-amber-900 sm:col-span-2">
          <input type="checkbox" checked={form.is_test_data} onChange={(event) => setForm({ ...form, is_test_data: event.target.checked })} disabled={saveMutation.isPending} />
          Explicitly mark this as test data eligible for owner-approved purge
        </label> : null}
        <label
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          className="focus-ring flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-line bg-slate-50 px-3 text-sm text-slate-700 hover:border-teal-400 hover:bg-teal-50 sm:col-span-2"
        >
          <ImagePlus size={16} />
          {imageFile ? imageFile.name : "Upload or drop image"}
          <span className="text-xs text-slate-500">JPG, PNG or WEBP up to 5MB. Large images are compressed automatically.</span>
          <input className="hidden" type="file" accept=".jpg,.jpeg,.png,.webp" onChange={(event) => void chooseImage(event.target.files?.[0] ?? null)} disabled={saveMutation.isPending} />
        </label>
        <div className="flex items-center gap-3 sm:col-span-2">
          {imagePreview || editing?.image_url ? <img src={imagePreview || imageSrc(editing?.image_url)} alt="" className="h-14 w-14 rounded object-cover" /> : <div className="grid h-14 w-14 place-items-center rounded bg-slate-100 text-slate-400"><PackageOpen size={20} /></div>}
          {editing?.image_url ? <Button type="button" variant="secondary" size="sm" onClick={() => deleteImageMutation.mutate(editing.id)} disabled={deleteImageMutation.isPending}>Delete image</Button> : null}
        </div>
        {error ? <div className="sm:col-span-2"><ErrorState message={error} /></div> : null}
        <div className="sticky bottom-[-1.25rem] z-10 -mx-4 flex flex-col-reverse gap-2 border-t border-line bg-surface/95 px-4 py-3 shadow-[0_-8px_16px_-16px_rgb(15_23_42/0.45)] backdrop-blur sm:col-span-2 sm:-mx-6 sm:flex-row sm:justify-end sm:px-6">
          <Button type="button" variant="secondary" onClick={cancelEdit} disabled={saveMutation.isPending}>Cancel</Button>
          <Button type="submit" disabled={saveMutation.isPending}>
            <Plus size={16} /> {saveMutation.isPending ? "Saving" : editing ? "Update product" : "Add product"}
          </Button>
          <Button type="button" variant="secondary" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate({ print: true })}>
            <Barcode size={16} /> {saveMutation.isPending ? "Saving" : "Save & Print Barcode"}
          </Button>
        </div>
      </form>
      </Dialog>

      {selectedCount ? (
        <div className="mb-4 grid gap-2 rounded-md border border-teal-200 bg-teal-50 p-3 md:grid-cols-[auto_1fr] md:items-center">
          <div className="text-sm font-semibold text-teal-900">{selectedCount} product{selectedCount === 1 ? "" : "s"} selected</div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => void exportProducts("csv", true)}>Export selected</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void deactivateSelected()}>Deactivate</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => setSelectedIds(new Set())}>Clear selection</Button>
            {canPermanentlyDelete ? <Button type="button" size="sm" variant="destructive" onClick={() => void openPermanentDelete(Array.from(selectedIds))}>Permanently delete</Button> : null}
          </div>
        </div>
      ) : null}

      {productsQuery.isLoading ? (
        <SkeletonRows rows={7} />
      ) : productsQuery.error ? (
        <ErrorState message={productsQuery.error instanceof Error ? productsQuery.error.message : "Unable to load products"} />
      ) : products.length ? (
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <div className="divide-y divide-line md:hidden">
            {products.map((product) => (
              <article key={product.id} className={`p-4 ${selectedIds.has(product.id) ? "bg-teal-50/50" : ""}`}>
                <div className="flex items-start gap-3">
                  <input aria-label={`Select ${product.name}`} className="mt-4" type="checkbox" checked={selectedIds.has(product.id)} onChange={() => toggleSelected(product.id)} />
                  {product.image_url ? <img loading="lazy" src={imageSrc(product.image_url)} alt="" className="h-14 w-14 shrink-0 rounded-md object-cover" /> : <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-400"><PackageOpen size={20} /></div>}
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold text-slate-950"><HighlightText text={product.name} query={debouncedSearch} /></div>
                    <div className="mt-0.5 truncate text-xs text-slate-500"><HighlightText text={product.category?.name} query={debouncedSearch} /> · <HighlightText text={product.subcategory?.name} query={debouncedSearch} /> · <HighlightText text={product.brand?.name} query={debouncedSearch} /></div>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                      <span>{product.variants.length ? `${product.variants.length} sellable variant${product.variants.length === 1 ? "" : "s"}` : productVariantLabel(product)}</span>
                      <span>{product.sku || product.barcode || "No code"}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
                  <div>
                    <div className="font-semibold text-slate-950">{money(product.selling_price)}</div>
                    <div className={`text-xs ${product.current_stock === 0 ? "text-rose-700" : product.current_stock <= product.minimum_stock ? "text-amber-700" : "text-slate-500"}`}>{product.current_stock} in stock</div>
                  </div>
                  <div className="flex gap-1">
                    <Button type="button" variant="secondary" size="sm" onClick={() => beginEdit(product)}><Edit3 size={15} /> Edit</Button>
                    {product.variants.length ? <Button type="button" variant="secondary" size="sm" onClick={() => toggleExpanded(product.id)}>{expandedIds.has(product.id) ? "Hide variants" : "Variants"}</Button> : null}
                    <Button type="button" variant="ghost" size="icon" onClick={() => setPrintTarget(product)} title="Print barcode"><Barcode size={16} /></Button>
                    {canPermanentlyDelete ? <Button type="button" variant="ghost" size="icon" className="text-rose-700" onClick={() => void openPermanentDelete([product.id])} title="Permanently delete product"><Trash2 size={16} /></Button> : null}
                  </div>
                </div>
                {expandedIds.has(product.id) ? <div className="mt-3 space-y-2 border-t border-line pt-3">{product.variants.map((variant) => <div key={variant.id} className="flex items-center justify-between gap-3 rounded-md bg-slate-50 p-3 text-xs"><div className="min-w-0"><p className="font-semibold text-slate-900">{variant.size || "Standard"}{variant.color ? ` · ${variant.color}` : ""}</p><p className="truncate font-mono text-slate-500">{variant.internal_sku} · {variant.scan_unit === "PACK" ? `Pack × ${variant.pieces_per_pack}` : "Piece"}</p></div><Button type="button" size="sm" variant="secondary" onClick={() => setManagedVariant({ product, variant })}>Manage</Button></div>)}</div> : null}
              </article>
            ))}
          </div>
          <div className="hidden overflow-x-auto md:block">
          <table className="min-w-[960px] divide-y divide-line text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3"><input type="checkbox" checked={products.length > 0 && products.every((product) => selectedIds.has(product.id))} onChange={toggleAllVisible} /></th>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">SKU / Barcode</th>
                <th className="px-4 py-3">Variant</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {products.map((product) => {
                const totalStock = product.variants.reduce((sum, variant) => sum + variant.current_stock, 0);
                const expanded = expandedIds.has(product.id);
                return (
                  <Fragment key={product.id}>
                    <tr className={selectedIds.has(product.id) ? "bg-teal-50/40" : ""}>
                      <td className="px-4 py-3"><input type="checkbox" checked={selectedIds.has(product.id)} onChange={() => toggleSelected(product.id)} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <button type="button" className="grid h-8 w-8 shrink-0 place-items-center rounded border border-line hover:bg-slate-50" onClick={() => toggleExpanded(product.id)} aria-label={`${expanded ? "Collapse" : "Expand"} ${product.name}`}>{expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</button>
                          {product.image_url ? <img loading="lazy" src={imageSrc(product.image_url)} alt="" className="h-11 w-11 rounded object-cover" /> : <div className="grid h-11 w-11 place-items-center rounded bg-slate-100 text-slate-400"><PackageOpen size={18} /></div>}
                          <div className="min-w-0">
                            <div className="truncate font-medium text-slate-900"><HighlightText text={product.name} query={debouncedSearch} /></div>
                            <div className="truncate text-slate-500"><HighlightText text={product.category?.name} query={debouncedSearch} /> / <HighlightText text={product.subcategory?.name} query={debouncedSearch} /> / <HighlightText text={product.brand?.name} query={debouncedSearch} /></div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div><HighlightText text={product.sku || "-"} query={debouncedSearch} /></div>
                        <div className="text-slate-500"><HighlightText text={product.barcode || "-"} query={debouncedSearch} /></div>
                      </td>
                      <td className="px-4 py-3">{product.variants.length ? `${product.variants.length} variant${product.variants.length === 1 ? "" : "s"}` : <span className="text-slate-500">No sellable variant</span>}</td>
                      <td className="px-4 py-3">{money(product.selling_price)}</td>
                      <td className="px-4 py-3">{money(product.purchase_price)}</td>
                      <td className="px-4 py-3">
                        <span className={totalStock === 0 ? "font-semibold text-rose-700" : totalStock <= product.minimum_stock ? "font-semibold text-amber-700" : "text-slate-700"}>
                          {totalStock}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded px-2 py-1 text-xs font-medium ${product.is_active ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-slate-600"}`}>
                          {product.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <Button type="button" variant="secondary" size="icon" onClick={() => beginEdit(product)} title="Edit product"><Edit3 size={16} /></Button>
                          <Button type="button" variant="ghost" size="icon" onClick={() => setPrintTarget(product)} title="Print base barcode"><Barcode size={16} /></Button>
                          {canPermanentlyDelete ? <Button type="button" variant="ghost" size="icon" className="text-rose-700 hover:bg-rose-50" onClick={() => void openPermanentDelete([product.id])} title="Permanently delete product"><Trash2 size={17} /></Button> : null}
                        </div>
                      </td>
                    </tr>
                    {expanded ? <tr className="bg-slate-50/60"><td className="px-4 py-4" colSpan={9}><div className="overflow-x-auto rounded-md border border-line bg-white"><table className="min-w-[980px] w-full text-left text-xs"><thead className="bg-slate-50 uppercase text-slate-500"><tr><th className="px-3 py-2">Size</th><th className="px-3 py-2">Colour</th><th className="px-3 py-2">Barcode</th><th className="px-3 py-2">SKU</th><th className="px-3 py-2">Scan</th><th className="px-3 py-2 text-right">MRP</th><th className="px-3 py-2 text-right">Selling</th><th className="px-3 py-2 text-right">Cost</th><th className="px-3 py-2 text-right">Stock</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Actions</th></tr></thead><tbody className="divide-y divide-line">{product.variants.map((variant) => <tr key={variant.id}><td className="px-3 py-2 font-semibold">{variant.size || "Standard"}</td><td className="px-3 py-2">{variant.color || "-"}</td><td className="px-3 py-2 font-mono">{variant.barcode}</td><td className="px-3 py-2 font-mono">{variant.internal_sku}</td><td className="px-3 py-2">{variant.scan_unit === "PACK" ? `Pack × ${variant.pieces_per_pack}` : "Piece"}</td><td className="px-3 py-2 text-right">{variant.mrp ? money(variant.mrp) : "-"}</td><td className="px-3 py-2 text-right font-semibold">{money(variant.selling_price)}</td><td className="px-3 py-2 text-right">{money(variant.average_cost || variant.last_purchase_cost)}</td><td className="px-3 py-2 text-right font-bold">{variant.current_stock}</td><td className="px-3 py-2"><span className={`rounded px-2 py-1 font-medium ${variant.is_active ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-slate-600"}`}>{variant.is_active ? "Active" : "Inactive"}</span></td><td className="px-3 py-2"><div className="flex gap-1"><Button type="button" variant="secondary" size="sm" onClick={() => setManagedVariant({ product, variant })}>Manage</Button><Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/stock-adjustment?variant_id=${variant.id}`)}>Adjust stock</Button><Button type="button" variant="ghost" size="icon" title="Print variant barcode" onClick={() => printVariantLabel(product, variant)}><Barcode size={15} /></Button></div></td></tr>)}</tbody></table></div></td></tr> : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          </div>
          <div className="flex flex-col gap-3 border-t border-line px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
            <div>{currentRange}</div>
            <div className="flex flex-wrap items-center gap-2">
              <select className="focus-ring h-9 rounded-md border border-line px-2" value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
                {[10, 25, 50, 100].map((size) => <option key={size} value={size}>{size} / page</option>)}
              </select>
              <Button type="button" variant="secondary" size="icon" disabled={!meta || meta.page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} title="Previous page"><ChevronLeft size={16} /></Button>
              <span>Page {meta?.page ?? 1} of {meta?.total_pages ?? 1}</span>
              <Button type="button" variant="secondary" size="icon" disabled={!meta || meta.page >= meta.total_pages} onClick={() => setPage((current) => current + 1)} title="Next page"><ChevronRight size={16} /></Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-line bg-white">
          <EmptyState
            icon={PackageOpen}
            title={isFiltered ? "No matching products" : "No products yet"}
            description={isFiltered ? "Try clearing filters or searching another SKU, barcode, brand, category, size, or color." : "Add products with images, SKU, barcode, price, stock, brand, and category."}
          />
        </div>
      )}

      <BarcodeLabelDialog open={Boolean(printTarget)} product={printTarget} onClose={() => setPrintTarget(null)} />
      {managedVariant ? <VariantManagementDialog key={managedVariant.variant.id} open product={managedVariant.product} variant={managedVariant.variant} canPermanentlyDelete={canPermanentlyDelete} onClose={() => setManagedVariant(null)} onSaved={invalidateProducts} onEditProduct={() => { const product = managedVariant.product; setManagedVariant(null); beginEdit(product); }} onUseExistingVariant={(variantId) => { const existing = managedVariant.product.variants.find((candidate) => candidate.id === variantId); if (existing) setManagedVariant({ product: managedVariant.product, variant: existing }); else { setManagedVariant(null); toast.error("Reload the product list before selecting the existing variant."); } }} /> : null}
      {newBarcode ? <ProductBarcodeDetailsDialog key={newBarcode} open barcode={newBarcode} onClose={() => setNewBarcode("")} onCreated={async (productId, variantId) => { invalidateProducts(); const product = await api.get<Product>(`/products/${productId}`); const variant = product.variants.find((candidate) => candidate.id === variantId); setNewBarcode(""); if (variant) setManagedVariant({ product, variant }); toast.success("Details added. No stock was created."); }} /> : null}
      {canPermanentlyDelete ? <BarcodeLookupDialog open={barcodeLookupOpen} products={products} onClose={() => setBarcodeLookupOpen(false)} onManageVariant={(variantId) => { const product = products.find((candidate) => candidate.variants.some((variant) => variant.id === variantId)); const variant = product?.variants.find((candidate) => candidate.id === variantId); if (product && variant) { setManagedVariant({ product, variant }); setBarcodeLookupOpen(false); } }} onChanged={() => { void productsQuery.refetch(); }} /> : null}
      <Dialog open={deleteDialogOpen} title={`Permanently delete ${deleteCheck ? deleteCheck.deletable.length + deleteCheck.blocked.length : selectedCount} product${(deleteCheck ? deleteCheck.deletable.length + deleteCheck.blocked.length : selectedCount) === 1 ? "" : "s"}?`} description="This action cannot be undone." onClose={() => setDeleteDialogOpen(false)} maxWidth="lg">
        {!deleteCheck ? <SkeletonRows rows={3} /> : <div className="space-y-5">
          {deleteCheck.deletable.length ? <section><h3 className="text-sm font-semibold text-foreground">Eligible for permanent deletion</h3><p className="mt-1 text-sm text-muted">The following products and their unused variants will be permanently removed.</p><ul className="mt-3 space-y-1 text-sm text-foreground">{deleteCheck.deletable.map((item) => <li key={item.product_id}>- {item.product_name}</li>)}</ul></section> : null}
          {deleteCheck.blocked.length ? <section className="rounded-lg border border-amber-200 bg-amber-50 p-4"><h3 className="text-sm font-semibold text-amber-950">Blocked products</h3><p className="mt-1 text-sm text-amber-900">Product cannot be deleted because it has stock or transaction history.</p><ul className="mt-3 space-y-3 text-sm text-amber-900">{deleteCheck.blocked.map((item) => { const product = products.find((candidate) => candidate.id === item.product_id); const currentStock = product?.variants.reduce((sum, variant) => sum + variant.current_stock, 0) ?? 0; return <li key={item.product_id} className="rounded-lg bg-white/60 p-3"><div className="font-medium">{item.product_name}</div><div className="mt-1 text-xs">{item.reason}</div><div className="mt-2 grid gap-1 text-xs sm:grid-cols-2"><span>Current stock: {currentStock}</span><span>Variant count: {item.references.variants ?? product?.variants.length ?? 0}</span><span>Inventory transaction count: {item.references.inventory_transactions ?? 0}</span><span>Sales dependencies: {item.references.sale_items ?? 0}</span><span>Purchase dependencies: {item.references.purchase_items ?? 0}</span></div><div className="mt-3 flex flex-wrap gap-2"><Button type="button" size="sm" variant="secondary" onClick={() => openStockAdjustmentForProduct(product ?? null)}>Correct stock</Button><Button type="button" size="sm" variant="secondary" onClick={() => { if (product) void api.post(`/products/${product.id}/archive`).then(() => { toast.success("Product archived"); invalidateProducts(); setDeleteDialogOpen(false); }).catch((cause: unknown) => toast.error(cause instanceof Error ? cause.message : "Unable to archive product")); }}><Archive size={14} /> Archive product</Button><Button type="button" size="sm" variant="secondary" onClick={() => navigate(`/stock?product_id=${item.product_id}`)}><History size={14} /> View history</Button></div></li>; })}</ul></section> : null}
          {deleteCheck.deletable.length ? <section className="rounded-lg border border-rose-200 bg-rose-50 p-4"><label className="field-label text-rose-950">Type DELETE to continue<input className="field-input mt-2" autoFocus value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} /></label><div className="mt-4 flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button><Button type="button" variant="destructive" disabled={deleteConfirmation !== "DELETE"} onClick={() => void confirmPermanentDelete()}>Permanently delete eligible</Button></div></section> : <div className="flex justify-end"><Button type="button" variant="secondary" onClick={() => setDeleteDialogOpen(false)}>Close</Button></div>}
          {canPermanentlyDelete && Array.from(selectedIds).some((id) => products.find((product) => product.id === id)?.is_test_data) ? <section className="border-t border-border pt-5"><h3 className="text-sm font-semibold text-foreground">Purge selected test products</h3><p className="mt-1 text-sm text-muted">Only explicitly marked test products can use this owner-only workflow.</p><label className="field-label mt-3">Type PURGE TEST DATA to continue<input className="field-input mt-2" value={purgeConfirmation} onChange={(event) => setPurgeConfirmation(event.target.value)} /></label><div className="mt-3 flex justify-end"><Button type="button" variant="destructive" disabled={purgeConfirmation !== "PURGE TEST DATA"} onClick={() => void purgeSelectedTestProducts()}>Purge selected test products</Button></div></section> : null}
        </div>}
      </Dialog>
      <Dialog open={Boolean(deleteResult)} title="Deletion completed" onClose={() => setDeleteResult(null)} maxWidth="md">
        <div className="space-y-4"><section><h3 className="text-sm font-semibold text-foreground">Deleted</h3>{deleteResult?.deleted.length ? <ul className="mt-2 space-y-1 text-sm">{deleteResult.deleted.map((item) => <li key={item.product_id}>- {item.product_name}</li>)}</ul> : <p className="mt-2 text-sm text-muted">No products were deleted.</p>}</section>{deleteResult?.blocked.length ? <section><h3 className="text-sm font-semibold text-foreground">Could not delete</h3><ul className="mt-2 space-y-2 text-sm">{deleteResult.blocked.map((item) => <li key={item.product_id}><div className="font-medium">{item.product_name}</div><div className="text-muted">{item.reason}</div></li>)}</ul></section> : null}<div className="flex justify-end"><Button type="button" onClick={() => setDeleteResult(null)}>Close</Button></div></div>
      </Dialog>
    </>
  );
}

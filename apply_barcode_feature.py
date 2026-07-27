#!/usr/bin/env python3
# Apply Rainbow Fashions product-date, barcode printing, and POS scanning changes.
# Usage: python3 apply_barcode_feature.py "/Users/subbu/Documents/shop inventory"

from __future__ import annotations
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
BACKUP = ROOT / ".barcode-feature-backup" / datetime.now().strftime("%Y%m%d-%H%M%S")
changed: list[str] = []


def die(message: str) -> None:
    raise SystemExit("ERROR: " + message)


def read(rel: str) -> tuple[Path, str]:
    path = ROOT / rel
    if not path.exists():
        die(f"Missing {rel}. Run from the shop inventory project root.")
    return path, path.read_text(encoding="utf-8")


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content:
        return
    if path.exists():
        target = BACKUP / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if rel not in changed:
        changed.append(rel)


def replace(rel: str, old: str, new: str, marker: str | None = None) -> None:
    _, text = read(rel)
    if marker and marker in text:
        return
    count = text.count(old)
    if count != 1:
        die(f"{rel}: expected one matching block, found {count}. No replacement was made for this step.")
    write(rel, text.replace(old, new, 1))


def replace_all(rel: str, old: str, new: str, expected: int, marker: str | None = None) -> None:
    _, text = read(rel)
    if marker and marker in text:
        return
    count = text.count(old)
    if count != expected:
        die(f"{rel}: expected {expected} matching blocks, found {count}.")
    write(rel, text.replace(old, new))


def insert_after(rel: str, needle: str, addition: str, marker: str) -> None:
    _, text = read(rel)
    if marker in text:
        return
    count = text.count(needle)
    if count != 1:
        die(f"{rel}: expected one insertion point, found {count}.")
    write(rel, text.replace(needle, needle + addition, 1))


# Backend model
replace("backend/app/models/product.py", "from datetime import datetime", "from datetime import date, datetime", "from datetime import date, datetime")
replace(
    "backend/app/models/product.py",
    "from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint",
    "from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint",
    "from sqlalchemy import Boolean, Date, DateTime",
)
insert_after(
    "backend/app/models/product.py",
    '    barcode: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True)\n',
    '    product_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())\n',
    "product_date: Mapped[date]",
)

# Backend schemas
replace(
    "backend/app/schemas/product.py",
    '    barcode: Optional[str] = Field(default=None, max_length=80)\n    image_url: Optional[str] = Field(default=None, max_length=500)\n    is_active: bool = True\n',
    '    barcode: Optional[str] = Field(default=None, max_length=80)\n    product_date: date = Field(default_factory=date.today)\n    image_url: Optional[str] = Field(default=None, max_length=500)\n    is_active: bool = True\n',
    "product_date: date = Field(default_factory=date.today)",
)
replace(
    "backend/app/schemas/product.py",
    '    barcode: Optional[str] = Field(default=None, max_length=80)\n    image_url: Optional[str] = Field(default=None, max_length=500)\n    is_active: Optional[bool] = None\n',
    '    barcode: Optional[str] = Field(default=None, max_length=80)\n    product_date: Optional[date] = None\n    image_url: Optional[str] = Field(default=None, max_length=500)\n    is_active: Optional[bool] = None\n',
    "product_date: Optional[date] = None",
)

# Repository exact lookup with relations
repo_method = '''    def get_by_barcode(self, barcode: str, exclude_id: Optional[UUID] = None) -> Optional[Product]:
        query = self.db.query(Product).filter(func.lower(Product.barcode) == barcode.strip().lower())
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

'''
insert_after(
    "backend/app/repositories/product.py",
    repo_method,
    '''    def get_by_barcode_with_relations(self, barcode: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand))
            .filter(func.lower(Product.barcode) == barcode.strip().lower())
            .first()
        )

''',
    "def get_by_barcode_with_relations",
)

# Product service
service_get = '''    def get(self, product_id: UUID) -> Product:
        product = self.repo.get_with_relations(product_id)
        if not product:
            raise not_found("Product")
        return product

'''
insert_after(
    "backend/app/services/product_service.py",
    service_get,
    '''    def get_by_barcode(self, barcode: str) -> Product:
        normalized = barcode.strip()
        if not normalized:
            raise bad_request("Barcode is required")
        product = self.repo.get_by_barcode_with_relations(normalized)
        if not product:
            raise not_found("Product")
        return product

''',
    "def get_by_barcode(self, barcode: str)",
)

old_create = '''    def create(self, payload: ProductCreate) -> Product:
        self._ensure_hierarchy(payload.category_id, payload.subcategory_id, payload.brand_id)
        self._validate_unique_variant(payload.category_id, payload.subcategory_id, payload.brand_id, payload.name, payload.size, payload.color)
        if payload.sku and self.repo.get_by_sku(payload.sku):
            raise conflict("SKU already exists")
        if payload.barcode and self.repo.get_by_barcode(payload.barcode):
            raise conflict("Barcode already exists")
        product = Product(**payload.model_dump())
        self.repo.add(product)
        self.db.commit()
        return self.get(product.id)
'''
new_create = '''    def create(self, payload: ProductCreate) -> Product:
        self._ensure_hierarchy(payload.category_id, payload.subcategory_id, payload.brand_id)
        self._validate_unique_variant(payload.category_id, payload.subcategory_id, payload.brand_id, payload.name, payload.size, payload.color)
        if payload.sku and self.repo.get_by_sku(payload.sku):
            raise conflict("SKU already exists")

        data = payload.model_dump()
        barcode = data.get("barcode") or self.generate_code("barcode")
        if self.repo.get_by_barcode(barcode):
            raise conflict("Barcode already exists")
        data["barcode"] = barcode

        product = Product(**data)
        self.repo.add(product)
        self.db.commit()
        return self.get(product.id)
'''
replace("backend/app/services/product_service.py", old_create, new_create, 'barcode = data.get("barcode") or self.generate_code("barcode")')
replace_all(
    "backend/app/services/product_service.py",
    'writer.writerow(["sku", "barcode", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])',
    'writer.writerow(["sku", "barcode", "product_date", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])',
    2,
    '"product_date", "name", "brand"',
)
replace(
    "backend/app/services/product_service.py",
    '''                product.barcode or "",
                product.name,
''',
    '''                product.barcode or "",
                product.product_date.isoformat(),
                product.name,
''',
    "product.product_date.isoformat()",
)
replace(
    "backend/app/services/product_service.py",
    '''                    barcode=row.get("barcode") or None,
                    category_id=category.id,
''',
    '''                    barcode=row.get("barcode") or None,
                    product_date=date.fromisoformat(row.get("product_date") or date.today().isoformat()),
                    category_id=category.id,
''',
    'product_date=date.fromisoformat(row.get("product_date")',
)
replace(
    "backend/app/services/product_service.py",
    'writer.writerow(["RF-SKU-SAMPLE", "890000000001", "Cotton Kurti", "Rainbow", "Kurtis", "General", "M", "Blue", "500", "799", "10", "2", "true"])',
    'writer.writerow(["RF-SKU-SAMPLE", "890000000001", date.today().isoformat(), "Cotton Kurti", "Rainbow", "Kurtis", "General", "M", "Blue", "500", "799", "10", "2", "true"])',
    '"890000000001", date.today().isoformat()',
)

# API route must stay before /{product_id}
create_route = '''@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)):
    return ProductService(db).create(payload)


'''
insert_after(
    "backend/app/api/routes/products.py",
    create_route,
    '''@router.get("/by-barcode/{barcode}", response_model=ProductRead)
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ProductService(db).get_by_barcode(barcode)


''',
    '@router.get("/by-barcode/{barcode}"',
)

# Migration based on the user's current 0009 head
migration_rel = "backend/alembic/versions/20260727_0010_product_date_barcode_scan.py"
if not (ROOT / migration_rel).exists():
    migration = '''# Add product date and complete barcode sales workflow.
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0010"
down_revision: Union[str, None] = "20260727_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("product_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=True))
    op.execute(sa.text("UPDATE products SET product_date = COALESCE(created_at::date, CURRENT_DATE) WHERE product_date IS NULL"))
    op.alter_column("products", "product_date", existing_type=sa.Date(), nullable=False)


def downgrade() -> None:
    op.drop_column("products", "product_date")
'''
    write(migration_rel, migration)

# Frontend type
replace(
    "frontend/src/types/index.ts",
    '  barcode?: string | null;\n  image_url?: string | null;\n',
    '  barcode?: string | null;\n  product_date: string;\n  image_url?: string | null;\n',
    "  product_date: string;",
)

# Printable Code 128-B label component; no npm dependency is needed.
component = r'''import { useEffect, useMemo, useState } from "react";
import { Printer } from "lucide-react";
import type { Product } from "../types";
import { money } from "../utils/format";
import Dialog from "./Dialog";
import { Button } from "./ui/button";

const CODE128_PATTERNS = [
  "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
  "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
  "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
  "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
  "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
  "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
  "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
  "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
  "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
  "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
  "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
  "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
  "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
  "211214", "211232", "2331112",
] as const;

interface Bar { x: number; width: number }

function encodeCode128B(value: string): { bars: Bar[]; width: number } | null {
  const characterValues = Array.from(value, (character) => character.charCodeAt(0) - 32);
  if (!characterValues.length || characterValues.some((code) => code < 0 || code > 94)) return null;
  const startCode = 104;
  const checksum = (startCode + characterValues.reduce((sum, code, index) => sum + code * (index + 1), 0)) % 103;
  const codes = [startCode, ...characterValues, checksum, 106];
  const bars: Bar[] = [];
  let x = 10;
  for (const code of codes) {
    Array.from(CODE128_PATTERNS[code]).forEach((moduleWidth, index) => {
      const width = Number(moduleWidth);
      if (index % 2 === 0) bars.push({ x, width });
      x += width;
    });
  }
  return { bars, width: x + 10 };
}

function Code128({ value }: { value: string }) {
  const encoded = useMemo(() => encodeCode128B(value), [value]);
  if (!encoded) return <div className="text-xs text-red-600">Unsupported barcode character.</div>;
  return (
    <svg aria-label={`Barcode ${value}`} className="h-16 w-full text-black" role="img" viewBox={`0 0 ${encoded.width} 52`} preserveAspectRatio="none">
      {encoded.bars.map((bar, index) => <rect key={`${bar.x}-${index}`} x={bar.x} y="0" width={bar.width} height="52" fill="currentColor" />)}
    </svg>
  );
}

function formatProductDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function Label({ product }: { product: Product }) {
  const barcode = product.barcode ?? "";
  return (
    <article className="barcode-label box-border flex min-h-[27mm] w-[47mm] flex-col justify-between overflow-hidden bg-white p-[1.5mm] text-black">
      <div>
        <div className="truncate text-[10pt] font-bold leading-tight">{product.name}</div>
        <div className="mt-0.5 flex justify-between gap-2 text-[7pt] leading-tight"><span>{product.size} · {product.color}</span><strong>{money(product.selling_price)}</strong></div>
        <div className="mt-0.5 text-[7pt] leading-tight">Date: {formatProductDate(product.product_date)}</div>
      </div>
      <div className="mt-1"><Code128 value={barcode} /><div className="mt-0.5 text-center font-mono text-[7pt] tracking-[0.08em]">{barcode}</div></div>
    </article>
  );
}

interface Props { open: boolean; product: Product | null; onClose: () => void; autoPrint?: boolean }

export default function BarcodeLabelDialog({ open, product, onClose, autoPrint = false }: Props) {
  const [copies, setCopies] = useState(1);
  useEffect(() => { if (!open) setCopies(1); }, [open]);
  useEffect(() => {
    if (!open || !product || !autoPrint) return;
    const timer = window.setTimeout(() => window.print(), 300);
    return () => window.clearTimeout(timer);
  }, [autoPrint, open, product]);
  if (!product) return null;
  const labels = Array.from({ length: copies }, (_, index) => <Label key={index} product={product} />);
  return (
    <>
      <style>{`@media print { body * { visibility: hidden !important; } #barcode-print-root, #barcode-print-root * { visibility: visible !important; } #barcode-print-root { display: block !important; position: absolute; inset: 0 auto auto 0; } .barcode-label { break-after: page; page-break-after: always; } .barcode-label:last-child { break-after: auto; page-break-after: auto; } @page { size: 50mm 30mm; margin: 1.5mm; } }`}</style>
      <Dialog open={open} title="Print barcode label" description={`${product.name} · ${product.barcode}`} onClose={onClose} maxWidth="md">
        <div className="space-y-4">
          <div className="mx-auto w-fit rounded-md border border-slate-200 bg-white p-2 shadow-sm"><Label product={product} /></div>
          <label className="field-label">Number of labels<input className="field-input" type="number" min="1" max="200" value={copies} onChange={(event) => setCopies(Math.min(200, Math.max(1, Number(event.target.value) || 1)))} /></label>
          <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose}>Close</Button><Button type="button" onClick={() => window.print()}><Printer size={16} /> Print labels</Button></div>
        </div>
      </Dialog>
      <div id="barcode-print-root" className="hidden">{labels}</div>
    </>
  );
}
'''
write("frontend/src/components/BarcodeLabelDialog.tsx", component)

# Products page
replace("frontend/src/pages/ProductsPage.tsx", "PackageOpen, Plus, RefreshCw, Search, Trash2, Wand2, X", "PackageOpen, Plus, Printer, RefreshCw, Search, Trash2, Wand2, X", "Plus, Printer, RefreshCw")
replace("frontend/src/pages/ProductsPage.tsx", 'import { api } from "../api/client";\n', 'import { api } from "../api/client";\nimport BarcodeLabelDialog from "../components/BarcodeLabelDialog";\n', 'import BarcodeLabelDialog from "../components/BarcodeLabelDialog";')
replace("frontend/src/pages/ProductsPage.tsx", '  barcode: string;\n  is_active: boolean;\n', '  barcode: string;\n  product_date: string;\n  is_active: boolean;\n', "  product_date: string;")
replace("frontend/src/pages/ProductsPage.tsx", '  barcode: "",\n  is_active: true,\n', '  barcode: "",\n  product_date: new Date().toISOString().slice(0, 10),\n  is_active: true,\n', "product_date: new Date().toISOString()")
replace("frontend/src/pages/ProductsPage.tsx", '    barcode: product.barcode ?? "",\n    is_active: product.is_active,\n', '    barcode: product.barcode ?? "",\n    product_date: product.product_date,\n    is_active: product.is_active,\n', "product_date: product.product_date")
replace("frontend/src/pages/ProductsPage.tsx", '  const [error, setError] = useState("");\n', '  const [error, setError] = useState("");\n  const [printProduct, setPrintProduct] = useState<Product | null>(null);\n  const [printOpen, setPrintOpen] = useState(false);\n', "const [printProduct, setPrintProduct]")
replace("frontend/src/pages/ProductsPage.tsx", '      ["selling_price", "Price is required"],\n', '      ["selling_price", "Price is required"],\n      ["product_date", "Product date is required"],\n', '["product_date", "Product date is required"]')
replace("frontend/src/pages/ProductsPage.tsx", '      barcode: form.barcode.trim() || null,\n      is_active: form.is_active,\n', '      barcode: form.barcode.trim() || null,\n      product_date: form.product_date,\n      is_active: form.is_active,\n', "product_date: form.product_date")

old_save = '''  const saveMutation = useMutation({
    mutationFn: async () => {
      const validationError = validateForm();
      if (validationError) throw new Error(validationError);
      const product = editing ? await api.put<Product>(`/products/${editing.id}`, payload()) : await api.post<Product>("/products", payload());
      if (imageFile) {
        const body = new FormData();
        body.append("file", imageFile);
        await api.post<Product>(`/products/${product.id}/image`, body);
      }
    },
    onSuccess: () => {
      toast.success(editing ? "Product updated" : "Product added");
      setForm(emptyForm);
      setEditing(null);
      setFormOpen(false);
      setImageFile(null);
      setError("");
      invalidateProducts();
    },
    onError: (err) => {
      const message = err instanceof Error ? err.message : "Unable to save product";
      setError(message);
      toast.error(message);
    },
  });
'''
new_save = '''  const saveMutation = useMutation({
    mutationFn: async ({ print }: { print: boolean }) => {
      const validationError = validateForm();
      if (validationError) throw new Error(validationError);
      let product = editing ? await api.put<Product>(`/products/${editing.id}`, payload()) : await api.post<Product>("/products", payload());
      if (imageFile) {
        const body = new FormData();
        body.append("file", imageFile);
        product = await api.post<Product>(`/products/${product.id}/image`, body);
      }
      return product;
    },
    onSuccess: (product, options) => {
      toast.success(editing ? "Product updated" : "Product added");
      setForm(emptyForm);
      setEditing(null);
      setFormOpen(false);
      setImageFile(null);
      setError("");
      if (options.print) {
        setPrintProduct(product);
        setPrintOpen(true);
      }
      invalidateProducts();
    },
    onError: (err) => {
      const message = err instanceof Error ? err.message : "Unable to save product";
      setError(message);
      toast.error(message);
    },
  });
'''
replace("frontend/src/pages/ProductsPage.tsx", old_save, new_save, 'mutationFn: async ({ print }: { print: boolean })')
replace("frontend/src/pages/ProductsPage.tsx", '      <form onSubmit={(event: FormEvent) => { event.preventDefault(); saveMutation.mutate(); }} className="grid gap-4 sm:grid-cols-2">', '      <form onSubmit={(event: FormEvent) => { event.preventDefault(); saveMutation.mutate({ print: false }); }} className="grid gap-4 sm:grid-cols-2">', "saveMutation.mutate({ print: false })")
barcode_field = '''        <label className="field-label">Barcode
        <div className="flex gap-2">
          <input className="field-input min-w-0 flex-1" placeholder="Optional" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} disabled={saveMutation.isPending} />
          <Button type="button" variant="secondary" size="icon" onClick={() => void generateCode("barcode")} title="Generate barcode"><Wand2 size={16} /></Button>
        </div>
        </label>
'''
insert_after("frontend/src/pages/ProductsPage.tsx", barcode_field, '''        <label className="field-label">Product date<span>*</span>
          <input className="field-input" type="date" value={form.product_date} onChange={(event) => setForm({ ...form, product_date: event.target.value })} disabled={saveMutation.isPending} />
        </label>
''', 'value={form.product_date}')
old_buttons = '''          <Button type="button" variant="secondary" onClick={cancelEdit} disabled={saveMutation.isPending}>Cancel</Button>
          <Button type="submit" disabled={saveMutation.isPending}>
            <Plus size={16} /> {saveMutation.isPending ? "Saving" : editing ? "Update product" : "Add product"}
          </Button>
'''
new_buttons = '''          <Button type="button" variant="secondary" onClick={cancelEdit} disabled={saveMutation.isPending}>Cancel</Button>
          <Button type="button" variant="secondary" onClick={() => saveMutation.mutate({ print: true })} disabled={saveMutation.isPending}>
            <Printer size={16} /> {saveMutation.isPending ? "Saving" : "Save & print"}
          </Button>
          <Button type="submit" disabled={saveMutation.isPending}>
            <Plus size={16} /> {saveMutation.isPending ? "Saving" : editing ? "Update product" : "Add product"}
          </Button>
'''
replace("frontend/src/pages/ProductsPage.tsx", old_buttons, new_buttons, '"Save & print"')
replace("frontend/src/pages/ProductsPage.tsx", '''      </Dialog>

      {selectedCount ? (
''', '''      </Dialog>

      <BarcodeLabelDialog
        open={printOpen}
        product={printProduct}
        autoPrint
        onClose={() => {
          setPrintOpen(false);
          setPrintProduct(null);
        }}
      />

      {selectedCount ? (
''', "<BarcodeLabelDialog")

# New Sale page
replace("frontend/src/pages/NewSalePage.tsx", 'import { FormEvent, useMemo, useRef, useState } from "react";', 'import { FormEvent, KeyboardEvent, useMemo, useRef, useState } from "react";', "FormEvent, KeyboardEvent")
replace("frontend/src/pages/NewSalePage.tsx", "ReceiptText, Search, ShoppingCart", "ReceiptText, ScanBarcode, ShoppingCart", "ReceiptText, ScanBarcode, ShoppingCart")
replace("frontend/src/pages/NewSalePage.tsx", '  const [completedSale, setCompletedSale] = useState<Sale | null>(null);\n', '  const [completedSale, setCompletedSale] = useState<Sale | null>(null);\n  const [lastScanned, setLastScanned] = useState<Product | null>(null);\n', "const [lastScanned, setLastScanned]")
add_product = '''  function addProduct(product: Product) {
    if (product.current_stock <= 0) { toast.error(`${product.name} is out of stock`); return; }
    setError("");
    setCart((current) => {
      const existing = current.find((line) => line.product.id === product.id);
      if (existing) {
        if (existing.quantity >= product.current_stock) { toast.error(`Only ${product.current_stock} units available`); return current; }
        return current.map((line) => line.product.id === product.id ? { ...line, quantity: line.quantity + 1 } : line);
      }
      return [...current, { product, quantity: 1 }];
    });
    setSearch("");
    searchRef.current?.focus();
  }

'''
insert_after("frontend/src/pages/NewSalePage.tsx", add_product, '''  const scanMutation = useMutation({
    mutationFn: (barcode: string) => api.get<Product>(`/products/by-barcode/${encodeURIComponent(barcode)}`),
    onSuccess: (product) => {
      setLastScanned(product);
      addProduct(product);
      toast.success(`${product.name} scanned`);
    },
    onError: (cause) => {
      const message = cause instanceof Error ? cause.message : "Barcode was not found";
      setLastScanned(null);
      setError(message);
      toast.error(message);
      searchRef.current?.select();
    },
  });

  function handleScanKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    const barcode = search.trim();
    if (!barcode) return;
    event.preventDefault();
    scanMutation.mutate(barcode);
  }

''', "const scanMutation = useMutation")
old_search = '''          <div className="mb-4 flex h-12 items-center rounded-lg border border-slate-200 bg-white px-4 shadow-sm"><Search size={19} className="shrink-0 text-slate-400" /><input ref={searchRef} autoFocus aria-label="Search or scan products" className="min-w-0 flex-1 border-0 px-3 outline-none" placeholder="Search product, SKU, or scan barcode" value={search} onChange={(event) => setSearch(event.target.value)} />{search ? <button type="button" onClick={() => setSearch("")} aria-label="Clear product search"><X size={18} className="text-slate-400" /></button> : null}</div>
'''
new_search = '''          <div className="mb-4 flex h-12 items-center rounded-lg border border-slate-200 bg-white px-4 shadow-sm">
            <ScanBarcode size={19} className="shrink-0 text-slate-400" />
            <input ref={searchRef} autoFocus aria-label="Search or scan products" className="min-w-0 flex-1 border-0 px-3 outline-none"
              placeholder="Search product, SKU, or scan barcode and press Enter" value={search}
              onChange={(event) => setSearch(event.target.value)} onKeyDown={handleScanKeyDown} />
            {scanMutation.isPending ? <span className="text-xs text-slate-400">Scanning…</span> : null}
            {search ? <button type="button" onClick={() => setSearch("")} aria-label="Clear product search"><X size={18} className="text-slate-400" /></button> : null}
          </div>
          {lastScanned ? (
            <div className="mb-4 rounded-lg border border-teal-200 bg-teal-50 p-4" aria-live="polite">
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-white text-teal-700"><ScanBarcode size={20} /></div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-slate-950">{lastScanned.name}</div>
                  <div className="mt-1 text-xs text-slate-600">{lastScanned.size} · {lastScanned.color} · {lastScanned.brand?.name}</div>
                  <div className="mt-2 grid gap-1 text-xs text-slate-700 sm:grid-cols-2">
                    <span>Barcode: <strong>{lastScanned.barcode}</strong></span>
                    <span>Date: <strong>{new Date(`${lastScanned.product_date}T00:00:00`).toLocaleDateString("en-IN")}</strong></span>
                    <span>Price: <strong>{money(lastScanned.selling_price)}</strong></span>
                    <span>Stock: <strong>{lastScanned.current_stock}</strong></span>
                  </div>
                </div>
                <button type="button" onClick={() => setLastScanned(null)} aria-label="Hide scanned product details"><X size={18} className="text-slate-500" /></button>
              </div>
            </div>
          ) : null}
'''
replace("frontend/src/pages/NewSalePage.tsx", old_search, new_search, "onKeyDown={handleScanKeyDown}")

print("Barcode feature patch applied.")
if changed:
    print("Changed files:")
    for rel in changed:
        print(" -", rel)
    print("Backups:", BACKUP.relative_to(ROOT))
else:
    print("No changes needed; the feature appears already applied.")
print("Next: cd backend && alembic upgrade head")
print("Then: python -m compileall backend/app")
print("Then: cd ../frontend && npm run typecheck && npm run build")

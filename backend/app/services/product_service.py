from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from math import ceil
from typing import Optional
from uuid import UUID
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.models.enums import StockMovementType
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_inventory import ProductInventory
from app.models.product_deletion_audit import ProductDeletionAudit
from app.models.product_update_audit import ProductUpdateAudit
from app.models.stock_history import StockHistory
from app.models.subcategory import SubCategory
from app.models.user import User
from app.repositories.product import ProductRepository
from app.schemas.product import (
    ProductBulkBrandUpdate,
    ProductBulkCategoryUpdate,
    ProductBulkIds,
    ProductBulkStockUpdate,
    ProductCreate,
    ProductImportSummary,
    ProductListResponse,
    ProductUpdate,
)
from app.services.file_service import FileService


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ProductRepository(db)

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        stock_status: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> list[Product]:
        return self.repo.list_with_relations(
            skip,
            limit,
            search,
            category_id,
            brand_id,
            is_active,
            stock_status,
            min_price,
            max_price,
            created_from,
            created_to,
            sort_by,
            sort_dir,
        )

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        stock_status: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> ProductListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        items, total = self.repo.list_paginated(
            page,
            page_size,
            search,
            category_id,
            brand_id,
            is_active,
            stock_status,
            min_price,
            max_price,
            created_from,
            created_to,
            sort_by,
            sort_dir,
        )
        return ProductListResponse(
            items=items,
            meta={
                "page": page,
                "page_size": page_size,
                "total_records": total,
                "total_pages": ceil(total / page_size) if total else 1,
            },
        )

    def get(self, product_id: UUID) -> Product:
        product = self.repo.get_with_relations(product_id)
        if not product:
            raise not_found("Product")
        return product

    def get_by_barcode(self, barcode: str, store_id: UUID | None = None) -> Product:
        normalized = barcode.strip()
        if not normalized:
            raise bad_request("Barcode is required")
        product = self.repo.get_by_barcode_with_relations(normalized, store_id) if store_id is not None else self.repo.get_by_barcode_with_relations(normalized)
        if not product:
            raise not_found("Product for this barcode")
        return product

    def create(self, payload: ProductCreate, store_id: UUID | None = None) -> Product:
        self._ensure_hierarchy(payload.category_id, payload.subcategory_id, payload.brand_id)
        self._validate_unique_product(payload.category_id, payload.subcategory_id, payload.brand_id, payload.name, store_id=store_id)
        if payload.sku and self.repo.get_by_sku(payload.sku):
            raise conflict("SKU already exists")
        barcode = payload.barcode or self.generate_code("barcode")
        if self.repo.get_by_barcode(barcode):
            raise conflict("Barcode already exists")
        colors = payload.colors or ([payload.color] if payload.color else [])
        sizes = payload.sizes or ([payload.size] if payload.size else [])
        product_data = payload.model_dump(exclude={"colors", "sizes"})
        product_data["store_id"] = store_id
        product_data["barcode"] = barcode
        product_data["color"] = colors[0] if colors else None
        product_data["size"] = sizes[0] if sizes else None
        product = Product(**product_data)
        self._replace_variants(product, colors, sizes)
        self.repo.add(product)
        self.db.commit()
        return self.get(product.id)

    def update(
        self,
        product_id: UUID,
        payload: ProductUpdate,
        store_id: UUID | None = None,
        current_user: User | None = None,
        request_id: str | None = None,
    ) -> Product:
        product = self.get(product_id)
        if store_id is not None and product.store_id != store_id:
            raise not_found("Product")
        data = payload.model_dump(exclude_unset=True)
        if "current_stock" in data:
            raise bad_request("Current stock cannot be edited directly. Use Stock Adjustment.", "STOCK_FIELDS_READ_ONLY")
        colors = data.pop("colors", None)
        sizes = data.pop("sizes", None)
        next_category_id = data.get("category_id", product.category_id)
        next_subcategory_id = data.get("subcategory_id", product.subcategory_id)
        next_brand_id = data.get("brand_id", product.brand_id)
        next_name = data.get("name", product.name)
        next_pricing_type = data.get("pricing_type", product.pricing_type)
        next_mrp = data.get("mrp", product.mrp)
        if next_pricing_type.value == "MRP" and next_mrp is None:
            raise bad_request("MRP is required when pricing_type is MRP")
        self._ensure_hierarchy(next_category_id, next_subcategory_id, next_brand_id)
        self._validate_unique_product(next_category_id, next_subcategory_id, next_brand_id, next_name, exclude_id=product_id, store_id=product.store_id)
        if data.get("sku") and self.repo.get_by_sku(data["sku"], exclude_id=product_id):
            raise conflict("SKU already exists")
        if data.get("barcode") and self.repo.get_by_barcode(data["barcode"], exclude_id=product_id):
            raise conflict("This barcode is already assigned to another variant.", "BARCODE_ALREADY_ASSIGNED")
        before_values = {key: self._audit_value(getattr(product, key)) for key in data}
        if colors is not None:
            before_values["colors"] = self._current_variant_values(product)[0]
        if sizes is not None:
            before_values["sizes"] = self._current_variant_values(product)[1]
        for key, value in data.items():
            setattr(product, key, value)
        if colors is not None or sizes is not None:
            existing_colors, existing_sizes = self._current_variant_values(product)
            next_colors = colors if colors is not None else existing_colors
            next_sizes = sizes if sizes is not None else existing_sizes
            product.color = next_colors[0] if next_colors else None
            product.size = next_sizes[0] if next_sizes else None
            self._sync_variants(product, next_colors, next_sizes)
        elif "color" in data or "size" in data:
            legacy_colors = [product.color] if product.color else []
            legacy_sizes = [product.size] if product.size else []
            self._sync_variants(product, legacy_colors, legacy_sizes)
        after_values = {key: self._audit_value(getattr(product, key)) for key in data}
        if colors is not None:
            after_values["colors"] = self._current_variant_values(product)[0]
        if sizes is not None:
            after_values["sizes"] = self._current_variant_values(product)[1]
        if current_user is not None and before_values != after_values:
            self._record_update_audit(product, current_user, request_id, "PRODUCT_UPDATE", before_values, after_values)
        self.db.commit()
        return self.get(product.id)

    def list_update_audits(self, product_id: UUID, current_user: User) -> list[ProductUpdateAudit]:
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == current_user.store_id).first()
        if not product:
            raise not_found("Product")
        return (
            self.db.query(ProductUpdateAudit)
            .filter(ProductUpdateAudit.product_id == product_id, ProductUpdateAudit.store_id == current_user.store_id)
            .order_by(ProductUpdateAudit.created_at.desc())
            .all()
        )

    def _record_update_audit(
        self,
        product: Product,
        current_user: User,
        request_id: str | None,
        change_source: str,
        before_values: dict,
        after_values: dict,
    ) -> None:
        self.db.add(
            ProductUpdateAudit(
                store_id=product.store_id,
                product_id=product.id,
                changed_by=current_user.id,
                changed_by_role=current_user.role.value,
                request_id=request_id or str(uuid4()),
                change_source=change_source,
                before_values=before_values,
                after_values=after_values,
            )
        )

    @staticmethod
    def _audit_value(value):
        if isinstance(value, (UUID, Decimal, date)):
            return str(value)
        if isinstance(value, list):
            return [ProductService._audit_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): ProductService._audit_value(item) for key, item in value.items()}
        return value

    def delete(self, product_id: UUID) -> None:
        raise bad_request("Use the owner-only typed permanent-delete workflow")

    def archive(self, product_id: UUID, current_user: User, request_id: str) -> Product:
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == current_user.store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        before = {"is_active": product.is_active, "variant_active": [variant.is_active for variant in product.variants]}
        product.is_active = False
        for variant in product.variants:
            variant.is_active = False
        self.db.add(ProductDeletionAudit(store_id=current_user.store_id, product_id=product.id, event_type="PRODUCT_ARCHIVED", delete_mode="ARCHIVE", reason=None, request_id=request_id, product_snapshot={"name": product.name, "before": before}, deleted_record_counts={}, performed_by=current_user.id, performed_by_role=current_user.role.value))
        self.db.commit()
        return self.get(product.id)

    def restore(self, product_id: UUID, current_user: User, request_id: str) -> Product:
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == current_user.store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        product.is_active = True
        for variant in product.variants:
            variant.is_active = True
        self.db.add(ProductDeletionAudit(store_id=current_user.store_id, product_id=product.id, event_type="PRODUCT_RESTORED", delete_mode="RESTORE", reason=None, request_id=request_id, product_snapshot={"name": product.name}, deleted_record_counts={}, performed_by=current_user.id, performed_by_role=current_user.role.value))
        self.db.commit()
        return self.get(product.id)

    async def upload_image(self, product_id: UUID, file: UploadFile, uploaded_by: UUID | None, current_user: User | None = None, request_id: str | None = None) -> Product:
        product = self.get(product_id)
        file_service = FileService(self.db)
        uploaded_file = await file_service.save_product_image(file, uploaded_by)
        previous_image = product.image_url
        file_service.delete_product_image_path(product.image_url)
        product.image_url = f"/uploads/products/{uploaded_file.stored_filename}"
        if current_user is not None:
            self._record_update_audit(product, current_user, request_id, "PRODUCT_IMAGE_UPLOAD", {"image_url": previous_image}, {"image_url": product.image_url})
        self.db.commit()
        return self.get(product.id)

    def delete_image(self, product_id: UUID, current_user: User | None = None, request_id: str | None = None) -> Product:
        product = self.get(product_id)
        previous_image = product.image_url
        FileService(self.db).delete_product_image_path(product.image_url)
        product.image_url = None
        if current_user is not None and previous_image is not None:
            self._record_update_audit(product, current_user, request_id, "PRODUCT_IMAGE_DELETE", {"image_url": previous_image}, {"image_url": None})
        self.db.commit()
        return self.get(product.id)

    def generate_code(self, kind: str) -> str:
        if kind not in {"sku", "barcode"}:
            raise bad_request("Code kind must be sku or barcode")
        prefix = "RF-SKU" if kind == "sku" else "RF"
        for _ in range(10):
            suffix = uuid4().hex[:10].upper()
            value = f"{prefix}-{suffix}" if kind == "sku" else f"{prefix}{suffix[:14]}"
            duplicate = self.repo.get_by_sku(value) if kind == "sku" else self.repo.get_by_barcode(value)
            if not duplicate:
                return value
        raise bad_request("Unable to generate a unique code")

    def bulk_delete(self, payload: ProductBulkIds) -> dict[str, int]:
        raise bad_request("Use the owner-only typed permanent-delete workflow")

    def bulk_update_category(self, payload: ProductBulkCategoryUpdate) -> dict[str, int]:
        if not self.db.get(Category, payload.category_id):
            raise not_found("Category")
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            self._ensure_hierarchy(payload.category_id, product.subcategory_id, product.brand_id)
            self._validate_unique_product(payload.category_id, product.subcategory_id, product.brand_id, product.name, product.id, product.store_id)
            product.category_id = payload.category_id
        self.db.commit()
        return {"updated": len(products)}

    def bulk_update_brand(self, payload: ProductBulkBrandUpdate) -> dict[str, int]:
        if not self.db.get(Brand, payload.brand_id):
            raise not_found("Brand")
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            self._ensure_hierarchy(product.category_id, product.subcategory_id, payload.brand_id)
            self._validate_unique_product(product.category_id, product.subcategory_id, payload.brand_id, product.name, product.id, product.store_id)
            product.brand_id = payload.brand_id
        self.db.commit()
        return {"updated": len(products)}

    def bulk_stock_update(self, payload: ProductBulkStockUpdate, current_user: User) -> dict[str, int]:
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            before_stock = product.current_stock
            after_stock = before_stock + payload.qty if payload.direction == "INCREASE" else before_stock - payload.qty
            if after_stock < 0:
                raise bad_request(f"Stock cannot become negative for {product.name}")
            product.current_stock = after_stock
            inventory = self._get_or_create_inventory(product.id, current_user.store_id)
            inventory.current_stock = after_stock
            self.db.add(
                StockHistory(
                    product_id=product.id,
                    store_id=current_user.store_id,
                    movement_type=StockMovementType.MANUAL_ADJUSTMENT,
                    qty=payload.qty,
                    before_stock=before_stock,
                    after_stock=after_stock,
                    reference=payload.reference or "Bulk stock update",
                    created_by=current_user.id,
                )
            )
        self.db.commit()
        return {"updated": len(products)}

    def export_csv(self, product_ids: Optional[list[UUID]] = None) -> str:
        products = self.repo.list_by_ids(product_ids) if product_ids else self.repo.list_with_relations(0, 10000)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["sku", "barcode", "product_date", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])
        for product in products:
            writer.writerow([
                product.sku or "",
                product.barcode or "",
                product.product_date.isoformat(),
                product.name,
                product.brand.name if product.brand else "",
                product.category.name if product.category else "",
                product.subcategory.name if product.subcategory else "",
                product.size,
                product.color,
                product.purchase_price,
                product.selling_price,
                product.current_stock,
                product.minimum_stock,
                product.is_active,
            ])
        return output.getvalue()

    def export_xlsx(self, product_ids: Optional[list[UUID]] = None) -> bytes:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise bad_request("XLSX export requires openpyxl to be installed") from exc
        products = self.repo.list_by_ids(product_ids) if product_ids else self.repo.list_with_relations(0, 10000)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Products"
        rows = csv.reader(StringIO(self.export_csv([product.id for product in products])))
        for row in rows:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def import_products(self, rows: list[dict[str, str]], update_existing: bool = False, store_id: UUID | None = None) -> ProductImportSummary:
        created = 0
        updated = 0
        errors: list[dict[str, str]] = []
        for index, row in enumerate(rows, start=2):
            try:
                category = self._find_category_by_name(row.get("category", ""))
                if not category:
                    raise ValueError("Category must already exist")
                brand = self._find_brand_by_name(category.id, row.get("brand", ""))
                subcategory = self._find_subcategory_by_name(category.id, row.get("subcategory", "General"))
                if not brand or not subcategory:
                    raise ValueError("Brand and subcategory must exist under the selected category")
                payload = ProductCreate(
                    sku=row.get("sku") or None,
                    barcode=row.get("barcode") or None,
                    product_date=date.fromisoformat((row.get("product_date") or "").strip()),
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    brand_id=brand.id,
                    name=row.get("name", ""),
                    size=row.get("size", ""),
                    color=row.get("color", ""),
                    purchase_price=Decimal(row.get("purchase_price", "0") or "0"),
                    selling_price=Decimal(row.get("selling_price", "0") or "0"),
                    pricing_type="OWN_PRICE",
                    current_stock=int(row.get("stock", "0") or "0"),
                    minimum_stock=int(row.get("minimum_stock", "0") or "0"),
                    is_active=str(row.get("active", "true")).lower() not in {"false", "0", "no"},
                )
                existing = self.repo.get_by_sku(payload.sku) if payload.sku else None
                if existing and update_existing:
                    self.update(existing.id, ProductUpdate(**payload.model_dump()))
                    updated += 1
                elif existing:
                    raise ValueError("SKU already exists")
                else:
                    self.create(payload, store_id)
                    created += 1
            except Exception as exc:
                errors.append({"row": str(index), "message": str(exc)})
                self.db.rollback()
        return ProductImportSummary(created=created, updated=updated, skipped=len(errors), errors=errors)

    def import_file_rows(self, file: UploadFile) -> list[dict[str, str]]:
        raise NotImplementedError("Use async route parser for uploaded files")

    def template_csv(self) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["sku", "barcode", "product_date", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])
        writer.writerow(["RF-SKU-SAMPLE", "RF00000000000001", date.today().isoformat(), "Cotton Kurti", "Rainbow", "Kurtis", "General", "M", "Blue", "500", "799", "10", "2", "true"])
        return output.getvalue()

    def _ensure_hierarchy(self, category_id: UUID, subcategory_id: UUID, brand_id: UUID) -> None:
        if not self.db.get(Category, category_id):
            raise not_found("Category")
        subcategory = self.db.get(SubCategory, subcategory_id)
        if not subcategory:
            raise not_found("Subcategory")
        brand = self.db.get(Brand, brand_id)
        if not brand:
            raise not_found("Brand")
        if subcategory.category_id != category_id:
            raise bad_request("Subcategory does not belong to the selected category")
        if brand.category_id != category_id:
            raise bad_request("Brand does not belong to the selected category")

    def _validate_unique_product(
        self,
        category_id: UUID,
        subcategory_id: UUID,
        brand_id: UUID,
        name: str,
        exclude_id: Optional[UUID] = None,
        store_id: Optional[UUID] = None,
    ) -> None:
        if not name or not name.strip():
            raise bad_request("Enter a product name.", "PRODUCT_NAME_REQUIRED")
        duplicate = self.repo.get_duplicate(category_id, subcategory_id, brand_id, name, exclude_id, store_id)
        if duplicate:
            raise conflict("A product with this name and brand already exists.", "PRODUCT_ALREADY_EXISTS")

    @staticmethod
    def _current_variant_values(product: Product) -> tuple[list[str], list[str]]:
        colors = list(dict.fromkeys(variant.color for variant in product.variants if variant.color))
        sizes = list(dict.fromkeys(variant.size for variant in product.variants if variant.size))
        if not colors and product.color:
            colors = [product.color]
        if not sizes and product.size:
            sizes = [product.size]
        return colors, sizes

    @staticmethod
    def _replace_variants(product: Product, colors: list[str], sizes: list[str]) -> None:
        product.variants.clear()
        if colors and sizes:
            combinations = ((color, size) for color in colors for size in sizes)
        elif colors:
            combinations = ((color, None) for color in colors)
        elif sizes:
            combinations = ((None, size) for size in sizes)
        else:
            return
        combination_values = list(combinations)
        stock_per_variant, remainder = divmod(product.current_stock, len(combination_values))
        for index, (color, size) in enumerate(combination_values, start=1):
            sku = f"RFV-{uuid4().hex[:12].upper()}"
            barcode = f"RFV{uuid4().hex[:14].upper()}"
            identity = "|".join((str(product.id or "pending"), (size or "").casefold(), (color or "").casefold(), "", str(product.mrp or product.selling_price), str(product.selling_price), str(index)))
            product.variants.append(
                ProductVariant(
                    store_id=product.store_id,
                    color=color,
                    size=size,
                    internal_sku=sku,
                    barcode=barcode,
                    identity_key=identity,
                    mrp=product.mrp,
                    selling_price=product.selling_price,
                    last_purchase_cost=product.purchase_price,
                    average_cost=product.purchase_price,
                    current_stock=stock_per_variant + (1 if index <= remainder else 0),
                )
            )

    @staticmethod
    def _sync_variants(product: Product, colors: list[str], sizes: list[str]) -> None:
        """Safely update existing variant labels without replacing variant records.

        Product variants are referenced by stock, purchase, sale, and barcode records.
        An edit form must never delete and recreate them simply because the product was
        renamed or a size/colour label was corrected.
        """
        if colors and sizes:
            targets = [(color, size) for color in colors for size in sizes]
        elif colors:
            targets = [(color, None) for color in colors]
        elif sizes:
            targets = [(None, size) for size in sizes]
        else:
            targets = []
        existing = list(product.variants)
        if len(targets) != len(existing):
            raise bad_request("Adding or removing variants requires the dedicated variant workflow.", "VARIANT_STRUCTURE_CHANGE_NOT_ALLOWED")
        if len(set(targets)) != len(targets):
            raise conflict("This size and colour variant already exists.", "VARIANT_ALREADY_EXISTS")
        remaining = list(targets)
        for variant in existing:
            pair = (variant.color, variant.size)
            if pair in remaining:
                remaining.remove(pair)
        for variant in existing:
            pair = (variant.color, variant.size)
            if pair in targets:
                continue
            color, size = remaining.pop(0)
            variant.color = color
            variant.size = size
            variant.identity_key = "|".join((str(product.id), (size or "").casefold(), (color or "").casefold(), (variant.style_code or "").casefold(), str(variant.mrp or variant.selling_price), str(variant.selling_price), str(variant.id)))

    def _products_for_bulk(self, product_ids: list[UUID]) -> list[Product]:
        products = self.repo.list_by_ids(product_ids)
        if len(products) != len(set(product_ids)):
            raise not_found("One or more products")
        return products

    def _get_or_create_inventory(self, product_id: UUID, store_id: Optional[UUID]) -> ProductInventory:
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
        inventory = (
            self.db.query(ProductInventory)
            .filter(ProductInventory.product_id == product_id, ProductInventory.store_id == store_id)
            .first()
        )
        if inventory:
            return inventory
        inventory = ProductInventory(product_id=product_id, store_id=store_id, current_stock=0, minimum_stock=0)
        self.db.add(inventory)
        self.db.flush()
        return inventory

    def _find_category_by_name(self, name: str) -> Optional[Category]:
        if not name:
            return None
        return self.db.query(Category).filter(Category.name.ilike(name.strip())).first()

    def _find_brand_by_name(self, category_id: UUID, name: str) -> Optional[Brand]:
        if not name:
            return None
        return self.db.query(Brand).filter(Brand.category_id == category_id, Brand.name.ilike(name.strip())).first()

    def _find_subcategory_by_name(self, category_id: UUID, name: str) -> Optional[SubCategory]:
        if not name:
            return None
        return self.db.query(SubCategory).filter(SubCategory.category_id == category_id, SubCategory.name.ilike(name.strip())).first()

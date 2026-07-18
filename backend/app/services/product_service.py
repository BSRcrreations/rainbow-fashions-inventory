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
from app.models.product_inventory import ProductInventory
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

    def create(self, payload: ProductCreate) -> Product:
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

    def update(self, product_id: UUID, payload: ProductUpdate) -> Product:
        product = self.get(product_id)
        data = payload.model_dump(exclude_unset=True)
        next_category_id = data.get("category_id", product.category_id)
        next_subcategory_id = data.get("subcategory_id", product.subcategory_id)
        next_brand_id = data.get("brand_id", product.brand_id)
        next_name = data.get("name", product.name)
        next_size = data.get("size", product.size)
        next_color = data.get("color", product.color)
        next_pricing_type = data.get("pricing_type", product.pricing_type)
        next_mrp = data.get("mrp", product.mrp)
        if next_pricing_type.value == "MRP" and next_mrp is None:
            raise bad_request("MRP is required when pricing_type is MRP")
        self._ensure_hierarchy(next_category_id, next_subcategory_id, next_brand_id)
        self._validate_unique_variant(next_category_id, next_subcategory_id, next_brand_id, next_name, next_size, next_color, exclude_id=product_id)
        if data.get("sku") and self.repo.get_by_sku(data["sku"], exclude_id=product_id):
            raise conflict("SKU already exists")
        if data.get("barcode") and self.repo.get_by_barcode(data["barcode"], exclude_id=product_id):
            raise conflict("Barcode already exists")
        for key, value in data.items():
            setattr(product, key, value)
        self.db.commit()
        return self.get(product.id)

    def delete(self, product_id: UUID) -> None:
        product = self.get(product_id)
        if self.repo.has_stock_history(product_id):
            raise conflict("Product has stock history and cannot be deleted; mark it inactive instead")
        image_url = product.image_url
        self.repo.delete(product)
        self.db.commit()
        FileService(self.db).delete_product_image_path(image_url)

    async def upload_image(self, product_id: UUID, file: UploadFile, uploaded_by: UUID | None) -> Product:
        product = self.get(product_id)
        file_service = FileService(self.db)
        uploaded_file = await file_service.save_product_image(file, uploaded_by)
        file_service.delete_product_image_path(product.image_url)
        product.image_url = f"/uploads/products/{uploaded_file.stored_filename}"
        self.db.commit()
        return self.get(product.id)

    def delete_image(self, product_id: UUID) -> Product:
        product = self.get(product_id)
        FileService(self.db).delete_product_image_path(product.image_url)
        product.image_url = None
        self.db.commit()
        return self.get(product.id)

    def generate_code(self, kind: str) -> str:
        if kind not in {"sku", "barcode"}:
            raise bad_request("Code kind must be sku or barcode")
        prefix = "RF-SKU" if kind == "sku" else "89"
        for _ in range(10):
            suffix = uuid4().hex[:10].upper()
            value = f"{prefix}-{suffix}" if kind == "sku" else f"{prefix}{suffix[:10]}"
            duplicate = self.repo.get_by_sku(value) if kind == "sku" else self.repo.get_by_barcode(value)
            if not duplicate:
                return value
        raise bad_request("Unable to generate a unique code")

    def bulk_delete(self, payload: ProductBulkIds) -> dict[str, int]:
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            FileService(self.db).delete_product_image_path(product.image_url)
            self.repo.delete(product)
        self.db.commit()
        return {"updated": len(products)}

    def bulk_update_category(self, payload: ProductBulkCategoryUpdate) -> dict[str, int]:
        if not self.db.get(Category, payload.category_id):
            raise not_found("Category")
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            self._ensure_hierarchy(payload.category_id, product.subcategory_id, product.brand_id)
            self._validate_unique_variant(payload.category_id, product.subcategory_id, product.brand_id, product.name, product.size, product.color, product.id)
            product.category_id = payload.category_id
        self.db.commit()
        return {"updated": len(products)}

    def bulk_update_brand(self, payload: ProductBulkBrandUpdate) -> dict[str, int]:
        if not self.db.get(Brand, payload.brand_id):
            raise not_found("Brand")
        products = self._products_for_bulk(payload.product_ids)
        for product in products:
            self._ensure_hierarchy(product.category_id, product.subcategory_id, payload.brand_id)
            self._validate_unique_variant(product.category_id, product.subcategory_id, payload.brand_id, product.name, product.size, product.color, product.id)
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
        writer.writerow(["sku", "barcode", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])
        for product in products:
            writer.writerow([
                product.sku or "",
                product.barcode or "",
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

    def import_products(self, rows: list[dict[str, str]], update_existing: bool = False) -> ProductImportSummary:
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
                    self.create(payload)
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
        writer.writerow(["sku", "barcode", "name", "brand", "category", "subcategory", "size", "color", "purchase_price", "selling_price", "stock", "minimum_stock", "active"])
        writer.writerow(["RF-SKU-SAMPLE", "890000000001", "Cotton Kurti", "Rainbow", "Kurtis", "General", "M", "Blue", "500", "799", "10", "2", "true"])
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

    def _validate_unique_variant(
        self,
        category_id: UUID,
        subcategory_id: UUID,
        brand_id: UUID,
        name: str,
        size: str,
        color: str,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        duplicate = self.repo.get_duplicate(category_id, subcategory_id, brand_id, name, size, color, exclude_id)
        if duplicate:
            raise conflict("Product variant already exists for this category, subcategory, brand, name, size, and color")

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

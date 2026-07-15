from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ProductRepository(db)

    def list(self, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> list[Product]:
        return self.repo.list_with_relations(skip, limit, search)

    def get(self, product_id: UUID) -> Product:
        product = self.repo.get_with_relations(product_id)
        if not product:
            raise not_found("Product")
        return product

    def create(self, payload: ProductCreate) -> Product:
        self._ensure_category_and_brand(payload.category_id, payload.brand_id)
        self._validate_unique_variant(payload.category_id, payload.brand_id, payload.name, payload.size, payload.color)
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
        next_brand_id = data.get("brand_id", product.brand_id)
        next_name = data.get("name", product.name)
        next_size = data.get("size", product.size)
        next_color = data.get("color", product.color)
        self._ensure_category_and_brand(next_category_id, next_brand_id)
        self._validate_unique_variant(next_category_id, next_brand_id, next_name, next_size, next_color, exclude_id=product_id)
        if data.get("barcode") and self.repo.get_by_barcode(data["barcode"], exclude_id=product_id):
            raise conflict("Barcode already exists")
        for key, value in data.items():
            setattr(product, key, value)
        self.db.commit()
        return self.get(product.id)

    def delete(self, product_id: UUID) -> None:
        product = self.get(product_id)
        self.repo.delete(product)
        self.db.commit()

    def _ensure_category_and_brand(self, category_id: UUID, brand_id: UUID) -> None:
        if not self.db.get(Category, category_id):
            raise not_found("Category")
        if not self.db.get(Brand, brand_id):
            raise not_found("Brand")

    def _validate_unique_variant(
        self,
        category_id: UUID,
        brand_id: UUID,
        name: str,
        size: str,
        color: str,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        duplicate = self.repo.get_duplicate(category_id, brand_id, name, size, color, exclude_id)
        if duplicate:
            raise conflict("Product variant already exists for this category, brand, name, size, and color")

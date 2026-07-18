from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.models.subcategory import SubCategory
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(func.lower(Category.name) == name.strip().lower()).first()

    def product_count(self, category_id: UUID) -> int:
        return self.db.query(Product).filter(Product.category_id == category_id).count()

    def list_hierarchy(self, skip: int = 0, limit: int = 100) -> list[Category]:
        return (
            self.db.query(Category)
            .options(selectinload(Category.brands), selectinload(Category.subcategories))
            .order_by(Category.name)
            .offset(skip)
            .limit(limit)
            .all()
        )


class BrandRepository(BaseRepository[Brand]):
    model = Brand

    def get_by_name(self, category_id: UUID, name: str) -> Optional[Brand]:
        return self.db.query(Brand).filter(Brand.category_id == category_id, func.lower(Brand.name) == name.strip().lower()).first()

    def list_by_category(self, category_id: Optional[UUID], skip: int = 0, limit: int = 100) -> list[Brand]:
        query = self.db.query(Brand)
        if category_id:
            query = query.filter(Brand.category_id == category_id)
        return query.order_by(Brand.name).offset(skip).limit(limit).all()

    def product_count(self, brand_id: UUID) -> int:
        return self.db.query(Product).filter(Product.brand_id == brand_id).count()


class SubCategoryRepository(BaseRepository[SubCategory]):
    model = SubCategory

    def get_by_name(self, category_id: UUID, name: str) -> Optional[SubCategory]:
        return self.db.query(SubCategory).filter(SubCategory.category_id == category_id, func.lower(SubCategory.name) == name.strip().lower()).first()

    def list_by_category(self, category_id: Optional[UUID], skip: int = 0, limit: int = 100) -> list[SubCategory]:
        query = self.db.query(SubCategory)
        if category_id:
            query = query.filter(SubCategory.category_id == category_id)
        return query.order_by(SubCategory.name).offset(skip).limit(limit).all()

    def product_count(self, subcategory_id: UUID) -> int:
        return self.db.query(Product).filter(Product.subcategory_id == subcategory_id).count()


def get_catalog_repositories(db: Session) -> tuple[CategoryRepository, BrandRepository]:
    return CategoryRepository(db), BrandRepository(db)

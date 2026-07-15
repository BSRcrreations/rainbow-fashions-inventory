from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.repositories.catalog import BrandRepository, CategoryRepository
from app.schemas.brand import BrandCreate, BrandUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

    def list(self, skip: int = 0, limit: int = 100) -> list[Category]:
        return self.repo.list(skip, limit)

    def get(self, category_id: UUID) -> Category:
        category = self.repo.get(category_id)
        if not category:
            raise not_found("Category")
        return category

    def create(self, payload: CategoryCreate) -> Category:
        if self.repo.get_by_name(payload.name):
            raise conflict("Category already exists")
        category = Category(**payload.model_dump())
        self.repo.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category_id: UUID, payload: CategoryUpdate) -> Category:
        category = self.get(category_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.repo.get_by_name(data["name"])
            if duplicate and duplicate.id != category.id:
                raise conflict("Category already exists")
        for key, value in data.items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: UUID) -> None:
        category = self.get(category_id)
        self.repo.delete(category)
        self.db.commit()


class BrandService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BrandRepository(db)

    def list(self, skip: int = 0, limit: int = 100) -> list[Brand]:
        return self.repo.list(skip, limit)

    def get(self, brand_id: UUID) -> Brand:
        brand = self.repo.get(brand_id)
        if not brand:
            raise not_found("Brand")
        return brand

    def create(self, payload: BrandCreate) -> Brand:
        if self.repo.get_by_name(payload.name):
            raise conflict("Brand already exists")
        brand = Brand(**payload.model_dump())
        self.repo.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def update(self, brand_id: UUID, payload: BrandUpdate) -> Brand:
        brand = self.get(brand_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.repo.get_by_name(data["name"])
            if duplicate and duplicate.id != brand.id:
                raise conflict("Brand already exists")
        for key, value in data.items():
            setattr(brand, key, value)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def delete(self, brand_id: UUID) -> None:
        brand = self.get(brand_id)
        self.repo.delete(brand)
        self.db.commit()

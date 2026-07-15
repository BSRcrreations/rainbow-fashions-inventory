from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.brand import Brand
from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(func.lower(Category.name) == name.strip().lower()).first()


class BrandRepository(BaseRepository[Brand]):
    model = Brand

    def get_by_name(self, name: str) -> Optional[Brand]:
        return self.db.query(Brand).filter(func.lower(Brand.name) == name.strip().lower()).first()


def get_catalog_repositories(db: Session) -> tuple[CategoryRepository, BrandRepository]:
    return CategoryRepository(db), BrandRepository(db)

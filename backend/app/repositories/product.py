from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    def list_with_relations(self, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> list[Product]:
        query = self.db.query(Product).options(joinedload(Product.category), joinedload(Product.brand))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.join(Product.category).join(Product.brand).filter(
                or_(
                    Product.name.ilike(pattern),
                    Product.color.ilike(pattern),
                    Product.size.ilike(pattern),
                    Product.barcode.ilike(pattern),
                    Brand.name.ilike(pattern),
                    Category.name.ilike(pattern),
                )
            )
        return query.order_by(Product.name.asc()).offset(skip).limit(limit).all()

    def get_with_relations(self, product_id: UUID) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .filter(Product.id == product_id)
            .first()
        )

    def get_duplicate(
        self,
        category_id: UUID,
        brand_id: UUID,
        name: str,
        size: str,
        color: str,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[Product]:
        query = self.db.query(Product).filter(
            Product.category_id == category_id,
            Product.brand_id == brand_id,
            Product.name == name.strip(),
            Product.size == size.strip(),
            Product.color == color.strip(),
        )
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

    def get_by_barcode(self, barcode: str, exclude_id: Optional[UUID] = None) -> Optional[Product]:
        query = self.db.query(Product).filter(Product.barcode == barcode.strip())
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

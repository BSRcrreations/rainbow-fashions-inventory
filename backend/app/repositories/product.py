from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload

from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.stock_history import StockHistory
from app.models.subcategory import SubCategory
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    def has_stock_history(self, product_id: UUID) -> bool:
        return self.db.query(StockHistory.id).filter(StockHistory.product_id == product_id).first() is not None

    def list_with_relations(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        stock_status: Optional[Literal["low", "out", "in"]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> list[Product]:
        query = self._filtered_query(search, category_id, brand_id, is_active, stock_status, min_price, max_price, created_from, created_to)
        query = self._apply_sort(query, sort_by, sort_dir)
        return query.offset(skip).limit(limit).all()

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        stock_status: Optional[Literal["low", "out", "in"]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> tuple[list[Product], int]:
        query = self._filtered_query(search, category_id, brand_id, is_active, stock_status, min_price, max_price, created_from, created_to)
        total = query.count()
        offset = (page - 1) * page_size
        query = self._apply_sort(query, sort_by, sort_dir)
        return query.offset(offset).limit(page_size).all(), total

    def _filtered_query(
        self,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        stock_status: Optional[Literal["low", "out", "in"]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
    ):
        query = self.db.query(Product).options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), selectinload(Product.variants))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.join(Product.category).join(Product.subcategory).join(Product.brand).filter(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.color.ilike(pattern),
                    Product.size.ilike(pattern),
                    Product.variants.any(or_(ProductVariant.color.ilike(pattern), ProductVariant.size.ilike(pattern))),
                    Product.barcode.ilike(pattern),
                    Brand.name.ilike(pattern),
                    Category.name.ilike(pattern),
                    SubCategory.name.ilike(pattern),
                )
            )
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if brand_id:
            query = query.filter(Product.brand_id == brand_id)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        if stock_status == "out":
            query = query.filter(Product.current_stock == 0)
        elif stock_status == "low":
            query = query.filter(Product.current_stock > 0, Product.current_stock <= Product.minimum_stock)
        elif stock_status == "in":
            query = query.filter(Product.current_stock > Product.minimum_stock)
        if min_price is not None:
            query = query.filter(Product.selling_price >= min_price)
        if max_price is not None:
            query = query.filter(Product.selling_price <= max_price)
        if created_from:
            query = query.filter(Product.created_at >= datetime.combine(created_from, time.min))
        if created_to:
            query = query.filter(Product.created_at <= datetime.combine(created_to, time.max))
        return query

    def _apply_sort(self, query, sort_by: str, sort_dir: str):
        sort_columns = {
            "name": Product.name,
            "sku": Product.sku,
            "selling_price": Product.selling_price,
            "purchase_price": Product.purchase_price,
            "stock": Product.current_stock,
            "created_at": Product.created_at,
            "updated_at": Product.updated_at,
        }
        column = sort_columns.get(sort_by, Product.name)
        ordered_column = column.desc().nullslast() if sort_dir == "desc" else column.asc().nullslast()
        return query.order_by(ordered_column, Product.name.asc())

    def get_with_relations(self, product_id: UUID) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), selectinload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )

    def get_duplicate(
        self,
        category_id: UUID,
        subcategory_id: UUID,
        brand_id: UUID,
        name: str,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[Product]:
        query = self.db.query(Product).filter(
            Product.category_id == category_id,
            Product.subcategory_id == subcategory_id,
            Product.brand_id == brand_id,
            func.lower(Product.name) == name.strip().lower(),
        )
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

    def get_by_barcode(self, barcode: str, exclude_id: Optional[UUID] = None) -> Optional[Product]:
        query = self.db.query(Product).filter(func.lower(Product.barcode) == barcode.strip().lower())
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

    def get_by_barcode_with_relations(self, barcode: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), selectinload(Product.variants))
            .filter(func.lower(Product.barcode) == barcode.strip().lower())
            .first()
        )

    def get_by_sku(self, sku: str, exclude_id: Optional[UUID] = None) -> Optional[Product]:
        query = self.db.query(Product).filter(func.lower(Product.sku) == sku.strip().lower())
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return query.first()

    def list_by_ids(self, product_ids: list[UUID]) -> list[Product]:
        return self.db.query(Product).filter(Product.id.in_(product_ids)).all()

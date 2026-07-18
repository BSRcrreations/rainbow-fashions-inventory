from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.brand import BrandCreate
from app.schemas.category import CategoryCreate
from app.schemas.dashboard import DistributionItem
from app.schemas.product import ProductCreate
from app.services.catalog_service import BrandService, CategoryService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def refresh(self, _: object) -> None:
        return None


class FakeCatalogRepo:
    def __init__(self, duplicate: object | None = None, product_count: int = 0) -> None:
        self.duplicate = duplicate
        self.products = product_count
        self.deleted = False

    def get(self, record_id):
        return SimpleNamespace(id=record_id, name="Existing")

    def get_by_name(self, _: str):
        return self.duplicate

    def add(self, instance):
        instance.id = uuid4()
        return instance

    def product_count(self, _: object) -> int:
        return self.products

    def delete(self, _: object) -> None:
        self.deleted = True


class Stage1ValidationTests(unittest.TestCase):
    def test_dashboard_distribution_accepts_text_label(self) -> None:
        item = DistributionItem(label="In stock", value=5)

        self.assertEqual(item.label, "In stock")
        self.assertEqual(item.value, 5)

    def test_empty_category_name_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryCreate(name="  ", is_active=True)

    def test_empty_brand_name_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            BrandCreate(name="  ", is_active=True)

    def test_duplicate_category_name_returns_conflict(self) -> None:
        service = CategoryService.__new__(CategoryService)
        service.db = FakeDb()
        service.repo = FakeCatalogRepo(duplicate=SimpleNamespace(id=uuid4()))

        with self.assertRaises(HTTPException) as context:
            service.create(CategoryCreate(name="Sarees", is_active=True))

        self.assertEqual(context.exception.status_code, 409)

    def test_category_used_by_products_cannot_be_deleted(self) -> None:
        service = CategoryService.__new__(CategoryService)
        service.db = FakeDb()
        service.repo = FakeCatalogRepo(product_count=2)

        with self.assertRaises(HTTPException) as context:
            service.delete(uuid4())

        self.assertEqual(context.exception.status_code, 400)

    def test_brand_used_by_products_cannot_be_deleted(self) -> None:
        service = BrandService.__new__(BrandService)
        service.db = FakeDb()
        service.repo = FakeCatalogRepo(product_count=1)

        with self.assertRaises(HTTPException) as context:
            service.delete(uuid4())

        self.assertEqual(context.exception.status_code, 400)

    def test_product_requires_mrp_for_mrp_pricing(self) -> None:
        with self.assertRaises(ValidationError):
            ProductCreate(
                category_id=uuid4(),
                brand_id=uuid4(),
                name="Kurti",
                size="M",
                color="Blue",
                purchase_price=100,
                selling_price=120,
                pricing_type="MRP",
                current_stock=1,
                minimum_stock=0,
            )


if __name__ == "__main__":
    unittest.main()

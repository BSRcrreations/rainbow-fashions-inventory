from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.brand import BrandCreate
from app.schemas.category import CategoryCreate
from app.schemas.dashboard import DistributionItem
from app.schemas.product import ProductCreate
from app.models.enums import SaleStatus
from app.schemas.sale import SaleCreate, SaleUpdate, SaleVoidRequest
from app.schemas.purchase import ExtractedInvoice
from app.schemas.subcategory import SubCategoryCreate
from app.schemas.stock import StockAdjustmentCreate
from app.services.catalog_service import BrandService, CategoryService
from app.services.sale_service import SaleService


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

    def test_brand_requires_parent_category(self) -> None:
        with self.assertRaises(ValidationError):
            BrandCreate(name="Prisma", is_active=True)

    def test_subcategory_requires_parent_category(self) -> None:
        with self.assertRaises(ValidationError):
            SubCategoryCreate(name="General", is_active=True)

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
                subcategory_id=uuid4(),
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

    def test_product_allows_no_color_or_size(self) -> None:
        product = ProductCreate(
            category_id=uuid4(),
            subcategory_id=uuid4(),
            brand_id=uuid4(),
            name="Gift Card",
            purchase_price=0,
            selling_price=500,
            pricing_type="OWN_PRICE",
        )

        self.assertIsNone(product.color)
        self.assertIsNone(product.size)
        self.assertEqual(product.colors, [])
        self.assertEqual(product.sizes, [])

    def test_product_normalizes_multiple_variants(self) -> None:
        product = ProductCreate(
            category_id=uuid4(),
            subcategory_id=uuid4(),
            brand_id=uuid4(),
            name="T-Shirt",
            colors=[" Black ", "black", "White"],
            sizes=["M", " M ", "L"],
            purchase_price=200,
            selling_price=399,
            pricing_type="OWN_PRICE",
        )

        self.assertEqual(product.colors, ["Black", "White"])
        self.assertEqual(product.sizes, ["M", "L"])

    def test_sale_requires_positive_line_items(self) -> None:
        with self.assertRaises(ValidationError):
            SaleCreate(payment_mode="CASH", items=[])
        with self.assertRaises(ValidationError):
            SaleCreate(payment_mode="CASH", items=[{"product_id": uuid4(), "quantity": 0}])

    def test_sale_update_cannot_have_zero_items(self) -> None:
        with self.assertRaises(ValidationError):
            SaleUpdate(payment_mode="CASH", edit_reason="Correction", version=1, items=[])

    def test_extracted_invoice_accepts_a_real_date(self) -> None:
        invoice = ExtractedInvoice(date="2026-07-14")

        self.assertEqual(str(invoice.date), "2026-07-14")

    def test_purchase_document_routes_are_registered(self) -> None:
        from app.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/api/v1/purchase-documents/upload", paths)
        self.assertIn("/api/v1/purchase-documents/jobs/{job_id}", paths)
        self.assertIn("/api/v1/purchase-documents/{document_id}/retry", paths)

    def test_stale_sale_version_returns_conflict(self) -> None:
        service = SaleService.__new__(SaleService)
        with self.assertRaises(HTTPException) as context:
            service._validate_version(SimpleNamespace(version=2), 1)
        self.assertEqual(context.exception.status_code, 409)

    def test_void_restores_remaining_inventory_and_retains_invoice(self) -> None:
        sale_id, item_id, product_id, store_id, user_id = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
        sale = SimpleNamespace(id=sale_id, invoice_number="RF-1", status=SaleStatus.COMPLETED, version=1, items=[SimpleNamespace(id=item_id, product_id=product_id, quantity=3)])
        service = SaleService.__new__(SaleService)
        service.db = MagicMock()
        service._store_id = MagicMock(return_value=store_id)
        service._locked_sale = MagicMock(return_value=sale)
        service._returned_quantities = MagicMock(return_value={})
        service._locked_product_inventory = MagicMock(return_value=(SimpleNamespace(), SimpleNamespace()))
        service._adjust_stock = MagicMock()
        service._audit_snapshot = MagicMock(return_value={"status": "COMPLETED"})
        service.get = MagicMock(return_value=sale)

        result = service.void(sale_id, SaleVoidRequest(reason="Customer cancellation", version=1), SimpleNamespace(id=user_id, store_id=store_id))

        self.assertIs(result, sale)
        self.assertEqual(sale.status, SaleStatus.VOIDED)
        self.assertEqual(sale.version, 2)
        self.assertEqual(service._adjust_stock.call_args.args[2], 3)
        self.assertEqual(service._adjust_stock.call_args.args[3].value, "SALE_VOID")
        service.db.commit.assert_called_once()
        self.assertEqual(len(sale.items), 1)

    def test_second_void_is_rejected(self) -> None:
        service = SaleService.__new__(SaleService)
        service._store_id = MagicMock(return_value=uuid4())
        service._locked_sale = MagicMock(return_value=SimpleNamespace(status=SaleStatus.VOIDED))
        with self.assertRaises(HTTPException) as context:
            service.void(uuid4(), SaleVoidRequest(reason="Duplicate request", version=1), SimpleNamespace(store_id=uuid4()))
        self.assertEqual(context.exception.status_code, 400)

    def test_stock_adjustment_requires_auditable_reference(self) -> None:
        with self.assertRaises(ValidationError):
            StockAdjustmentCreate(product_id=uuid4(), direction="INCREASE", reason="MANUAL_ADJUSTMENT", qty=1, reference="")

    def test_stock_adjustment_rejects_generic_reason(self) -> None:
        with self.assertRaises(ValidationError):
            StockAdjustmentCreate(product_id=uuid4(), direction="INCREASE", reason="ADJUSTMENT", qty=1, reference="COUNT-1")


if __name__ == "__main__":
    unittest.main()

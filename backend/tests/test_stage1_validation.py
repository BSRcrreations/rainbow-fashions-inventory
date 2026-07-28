from __future__ import annotations

import unittest
from datetime import date
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
from app.schemas.purchase import PurchaseItemReview, PurchasePatch
from app.schemas.subcategory import SubCategoryCreate
from app.schemas.stock import StockAdjustmentCreate
from app.services.catalog_service import BrandService, CategoryService
from app.services.purchase_service import PurchaseService
from app.services.product_service import ProductService
from app.services.sale_service import SaleService
from app.models.brand import Brand
from app.models.category import Category


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

    def get_for_store(self, record_id, _store_id):
        return self.get(record_id)

    def get_by_name(self, *_):
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
        current_user = SimpleNamespace(store_id=uuid4())

        with self.assertRaises(HTTPException) as context:
            service.create(CategoryCreate(name="Sarees", is_active=True), current_user)

        self.assertEqual(context.exception.status_code, 409)

    def test_category_used_by_products_cannot_be_deleted(self) -> None:
        service = CategoryService.__new__(CategoryService)
        service.db = FakeDb()
        service.repo = FakeCatalogRepo(product_count=2)
        current_user = SimpleNamespace(store_id=uuid4())

        with self.assertRaises(HTTPException) as context:
            service.delete(uuid4(), current_user)

        self.assertEqual(context.exception.status_code, 400)

    def test_brand_used_by_products_cannot_be_deleted(self) -> None:
        service = BrandService.__new__(BrandService)
        service.db = FakeDb()
        service.repo = FakeCatalogRepo(product_count=1)
        current_user = SimpleNamespace(store_id=uuid4())

        with self.assertRaises(HTTPException) as context:
            service.delete(uuid4(), current_user)

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
                product_date=date.today(),
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
            product_date=date.today(),
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
            product_date=date.today(),
        )

        self.assertEqual(product.colors, ["Black", "White"])
        self.assertEqual(product.sizes, ["M", "L"])

    def test_product_date_is_required_and_serialized(self) -> None:
        with self.assertRaises(ValidationError):
            ProductCreate(
                category_id=uuid4(), subcategory_id=uuid4(), brand_id=uuid4(), name="Date test",
                purchase_price=10, selling_price=20, pricing_type="OWN_PRICE",
            )
        product = ProductCreate(
            category_id=uuid4(), subcategory_id=uuid4(), brand_id=uuid4(), name="Date test",
            purchase_price=10, selling_price=20, pricing_type="OWN_PRICE", product_date=date(2026, 7, 27),
        )
        self.assertEqual(product.product_date, date(2026, 7, 27))

    def test_product_create_generates_unique_barcode(self) -> None:
        service = ProductService.__new__(ProductService)
        service.db = FakeDb()
        service.repo = MagicMock()
        service.repo.get_by_sku.return_value = None
        service.repo.get_by_barcode.return_value = None
        service.repo.add.side_effect = lambda product: setattr(product, "id", uuid4())
        service._ensure_hierarchy = MagicMock()
        service._validate_unique_product = MagicMock()
        service._replace_variants = MagicMock()
        service.get = MagicMock(side_effect=lambda product_id: SimpleNamespace(id=product_id))
        payload = ProductCreate(
            category_id=uuid4(), subcategory_id=uuid4(), brand_id=uuid4(), name="Barcode test",
            purchase_price=10, selling_price=20, pricing_type="OWN_PRICE", product_date=date.today(),
        )

        service.create(payload)

        created = service.repo.add.call_args.args[0]
        self.assertTrue(created.barcode.startswith("RF"))
        self.assertGreater(len(created.barcode), 10)
        self.assertTrue(service.db.committed)

    def test_manual_duplicate_barcode_is_rejected(self) -> None:
        service = ProductService.__new__(ProductService)
        service.db = FakeDb()
        service.repo = MagicMock()
        service.repo.get_by_sku.return_value = None
        service.repo.get_by_barcode.return_value = SimpleNamespace(id=uuid4())
        service._ensure_hierarchy = MagicMock()
        service._validate_unique_product = MagicMock()
        payload = ProductCreate(
            category_id=uuid4(), subcategory_id=uuid4(), brand_id=uuid4(), name="Duplicate code",
            purchase_price=10, selling_price=20, pricing_type="OWN_PRICE", product_date=date.today(), barcode="RF1234567890",
        )

        with self.assertRaises(HTTPException) as context:
            service.create(payload)

        self.assertEqual(context.exception.status_code, 409)

    def test_exact_barcode_lookup_and_unknown_barcode(self) -> None:
        service = ProductService.__new__(ProductService)
        service.repo = MagicMock()
        found = SimpleNamespace(id=uuid4(), barcode="RF123")
        service.repo.get_by_barcode_with_relations.return_value = found
        self.assertIs(service.get_by_barcode(" RF123 "), found)
        service.repo.get_by_barcode_with_relations.assert_called_once_with("RF123")
        service.repo.get_by_barcode_with_relations.return_value = None
        with self.assertRaises(HTTPException) as context:
            service.get_by_barcode("UNKNOWN")
        self.assertEqual(context.exception.status_code, 404)

    def test_barcode_route_precedes_dynamic_product_route(self) -> None:
        from app.main import app

        paths = [route.path for route in app.routes]
        barcode_index = paths.index("/api/v1/products/barcode/{barcode}")
        product_index = paths.index("/api/v1/products/{product_id}")
        self.assertLess(barcode_index, product_index)

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

    def test_purchase_patch_allows_partial_invoice_update(self) -> None:
        patch = PurchasePatch(invoice_number="DS/26-27/05-A", version=4)

        self.assertEqual(patch.invoice_number, "DS/26-27/05-A")
        self.assertEqual(patch.version, 4)
        self.assertEqual(patch.model_fields_set, {"invoice_number", "version"})

    def test_purchase_item_allows_optional_size_and_colour(self) -> None:
        item = PurchaseItemReview(product_name="Gift box", quantity=1, purchase_price=100, line_total=100)

        self.assertEqual(item.size, "")
        self.assertEqual(item.color, "")

    def test_purchase_item_catalog_selection_is_synchronized_and_validated(self) -> None:
        category_id, other_category_id, brand_id = uuid4(), uuid4(), uuid4()
        store_id = uuid4()
        category = SimpleNamespace(id=category_id, name="Bras")
        other_category = SimpleNamespace(id=other_category_id, name="Leggings")
        brand = SimpleNamespace(id=brand_id, category_id=category_id, name="Jockey")
        service = PurchaseService.__new__(PurchaseService)
        service.db = MagicMock()
        service.db.query.return_value.filter.return_value.first.side_effect = [category, brand, other_category, brand]
        current_user = SimpleNamespace(store_id=store_id)

        item = SimpleNamespace(category_id=category_id, category_name=None, brand_id=brand_id, brand_name=None)
        service._synchronize_item_catalog(item, current_user)

        self.assertEqual(item.category_name, "Bras")
        self.assertEqual(item.brand_name, "Jockey")
        item.category_id = other_category_id
        with self.assertRaises(HTTPException) as context:
            service._synchronize_item_catalog(item, current_user)
        self.assertEqual(context.exception.status_code, 400)

    def test_stale_purchase_version_returns_purchase_modified_code(self) -> None:
        service = PurchaseService.__new__(PurchaseService)
        with self.assertRaises(HTTPException) as context:
            service._validate_version(SimpleNamespace(version=2), 1)

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail["code"], "PURCHASE_MODIFIED")

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

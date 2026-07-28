from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.models.enums import UserRole
from app.services.product_deletion_service import ProductDeletionService


class DeleteDb:
    def __init__(self, fail_delete: bool = False) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.committed = False
        self.rolled_back = False
        self.fail_delete = fail_delete

    def add(self, record: object) -> None:
        self.added.append(record)

    def delete(self, record: object) -> None:
        if self.fail_delete:
            raise RuntimeError("database failure")
        self.deleted.append(record)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _product_fixture(name: str = "Test product") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        sku="TEST-001",
        barcode="RFTEST001",
        image_url=None,
        category=SimpleNamespace(name="Test category"),
        brand=SimpleNamespace(name="Test brand"),
        variants=[SimpleNamespace(color="Blue", size="M")],
        is_test_data=True,
    )


def _owner_fixture() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), store_id=uuid4(), role=UserRole.OWNER)


class ProductDeletionServiceTests(unittest.TestCase):
    def test_confirmation_must_match_exactly(self) -> None:
        with self.assertRaises(HTTPException) as context:
            ProductDeletionService._require_confirmation("delete", "DELETE", "request-1")

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail["code"], "DELETE_CONFIRMATION_REQUIRED")

    def test_unused_product_is_deleted_with_a_durable_snapshot(self) -> None:
        db = DeleteDb()
        service = ProductDeletionService(db)
        product = _product_fixture()
        user = _owner_fixture()
        service._completed_products_for_request = lambda *_: set()  # type: ignore[method-assign]
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": {}}  # type: ignore[method-assign]
        service._counts = lambda *_args: {"variants": 1, "physical_stock": 0}  # type: ignore[method-assign]

        result = service.permanently_delete([product.id], "DELETE", user, "request-2")

        self.assertTrue(db.committed)
        self.assertEqual(db.deleted, [product])
        self.assertEqual(result["deleted"][0]["product_name"], product.name)
        audit = db.added[0]
        self.assertEqual(audit.event_type, "PRODUCT_PERMANENTLY_DELETED")
        self.assertEqual(audit.product_snapshot["barcode"], "RFTEST001")

    def test_product_with_stock_is_blocked_by_preflight(self) -> None:
        service = ProductDeletionService(DeleteDb())
        product = _product_fixture("Stocked product")
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
            "reason": "Stocked product still has 4 units in stock.",
            "code": "PRODUCT_HAS_STOCK",
            "references": {"physical_stock": 4, "sale_items": 0},
        }

        result = service.check([product.id], _owner_fixture(), "request-stock")

        self.assertEqual(result["deletable"], [])
        self.assertEqual(result["blocked"][0]["code"], "PRODUCT_HAS_STOCK")
        self.assertEqual(result["blocked"][0]["references"]["physical_stock"], 4)

    def test_delete_rolls_back_when_any_product_delete_fails(self) -> None:
        db = DeleteDb(fail_delete=True)
        service = ProductDeletionService(db)
        product = _product_fixture()
        service._completed_products_for_request = lambda *_: set()  # type: ignore[method-assign]
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": {}}  # type: ignore[method-assign]
        service._counts = lambda *_args: {}  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            service.permanently_delete([product.id], "DELETE", _owner_fixture(), "request-3")

        self.assertTrue(db.rolled_back)

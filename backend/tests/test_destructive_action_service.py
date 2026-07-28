from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.models.enums import SaleStatus, StockMovementType, UserRole
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.services.deletion_security_service import DeletePasswordInvalidError
from app.services.destructive_action_service import DestructiveActionService


class _Query:
    def __init__(self, value: object) -> None:
        self.value = value

    def filter(self, *_args: object) -> _Query:
        return self

    def with_for_update(self) -> _Query:
        return self

    def one(self) -> object:
        return self.value

    def one_or_none(self) -> object:
        return self.value


class _Db:
    def __init__(self, product: object | None = None, inventory: object | None = None) -> None:
        self.product = product
        self.inventory = inventory
        self.added: list[object] = []

    def query(self, model: object) -> _Query:
        return _Query(self.product if model is Product else self.inventory)

    def add(self, record: object) -> None:
        self.added.append(record)

    def flush(self) -> None:
        return None


def _owner() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), store_id=uuid4(), role=UserRole.OWNER)


class DestructiveActionServiceTests(unittest.TestCase):
    def test_idempotency_key_error_keeps_request_id(self) -> None:
        service = DestructiveActionService(_Db())
        with self.assertRaises(HTTPException) as context:
            service._idempotent("SALE_DELETE", [uuid4()], "", _owner(), "request-123")
        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail["request_id"], "request-123")

    def test_sale_void_restores_stock_and_keeps_invoice(self) -> None:
        store_id = uuid4()
        product = SimpleNamespace(id=uuid4(), current_stock=3)
        inventory = SimpleNamespace(product_id=product.id, store_id=store_id, current_stock=3)
        db = _Db(product, inventory)
        service = DestructiveActionService(db)
        user = SimpleNamespace(id=uuid4(), store_id=store_id, role=UserRole.OWNER)
        item = SimpleNamespace(id=uuid4(), product_id=product.id, quantity=2)
        sale = SimpleNamespace(id=uuid4(), invoice_number="RF-100", items=[item], status=SaleStatus.COMPLETED, version=4, voided_by=None, voided_at=None)
        reversal_ids = service._void_sale(sale, user, "request-456")
        self.assertEqual(product.current_stock, 5)
        self.assertEqual(inventory.current_stock, 5)
        self.assertEqual(sale.status, SaleStatus.VOIDED)
        self.assertEqual(sale.version, 5)
        movement = next(record for record in db.added if getattr(record, "movement_type", None) == StockMovementType.SALE_VOID)
        self.assertEqual(movement.qty, 2)
        self.assertEqual(len(reversal_ids), 1)
        self.assertIsNotNone(sale.items)

    def test_password_failure_returns_safe_message(self) -> None:
        service = DestructiveActionService(_Db())
        user = _owner()
        service.db.query = lambda *_args: SimpleNamespace(filter=lambda *_args: SimpleNamespace(scalar=lambda: 0))  # type: ignore[method-assign]
        service.db.add = lambda _record: None  # type: ignore[method-assign]
        service.db.get = lambda *_args: None  # type: ignore[attr-defined]
        service.db.commit = lambda: None  # type: ignore[attr-defined]
        with patch("app.services.destructive_action_service.verify_delete_password", side_effect=DeletePasswordInvalidError("invalid")), patch.object(service, "_audit"):
            with self.assertRaises(HTTPException) as context:
                service._verify_password("wrong", user, "request-789", None)
        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail["code"], "DELETE_PASSWORD_INVALID")

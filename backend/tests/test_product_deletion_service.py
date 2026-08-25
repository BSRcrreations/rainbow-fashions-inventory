from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.models.enums import UserRole
from app.models.product_barcode import ProductBarcode, ProductBarcodeVariantTarget
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


class BarcodeCleanupQuery:
    def __init__(self, db: "BarcodeCleanupDb", model: object) -> None:
        self.db, self.model = db, model

    def filter(self, *_args: object) -> "BarcodeCleanupQuery":
        return self

    def with_for_update(self) -> "BarcodeCleanupQuery":
        return self

    def all(self) -> list[SimpleNamespace]:
        return list(self.db.mappings) if self.model is ProductBarcode else []

    def first(self) -> SimpleNamespace | None:
        if self.model is ProductBarcodeVariantTarget:
            return self.db.survivors.pop(0) if self.db.survivors else None
        return None

    def delete(self, **_kwargs: object) -> int:
        self.db.bulk_deletes.append(self.model)
        return 1


class BarcodeCleanupDb(DeleteDb):
    def __init__(self, mappings: list[SimpleNamespace], survivors: list[SimpleNamespace | None], survivor_variant: SimpleNamespace | None = None) -> None:
        super().__init__()
        self.mappings, self.survivors, self.survivor_variant = mappings, survivors, survivor_variant
        self.bulk_deletes: list[object] = []

    def query(self, model: object, *_args: object) -> BarcodeCleanupQuery:
        return BarcodeCleanupQuery(self, model)

    def get(self, model: object, _identifier: object) -> SimpleNamespace | None:
        return self.survivor_variant


def _variant_fixture() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(), color="Blue", size="M", internal_sku="TEST-001-BLU-M",
        barcode="RFTEST001", mrp=199, selling_price=150, last_purchase_cost=100,
    )


def _product_fixture(name: str = "Test product", variants: int = 1) -> SimpleNamespace:
    product = SimpleNamespace(
        id=uuid4(), name=name, sku="TEST-001", barcode="RFTEST001", image_url=None,
        category=SimpleNamespace(name="Test category"), brand=SimpleNamespace(name="Test brand"),
        variants=[_variant_fixture() for _ in range(variants)], is_test_data=True,
        purchase_price=100, selling_price=150, mrp=199,
    )
    for variant in product.variants:
        variant.product_id = product.id
    return product


def _owner_fixture() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), store_id=uuid4(), role=UserRole.OWNER)


def _counts(**overrides: int) -> dict[str, int]:
    values = {
        "inventory_transactions": 0, "purchase_items": 0, "sale_items": 0,
        "inventory_records": 1, "variants": 1, "variant_stock": 0,
        "aggregate_product_stock": 0, "active_cost_lot_pieces": 0,
        "protected_transactions": 0, "physical_stock": 0,
    }
    values.update(overrides)
    return values


class ProductDeletionServiceTests(unittest.TestCase):
    def test_confirmation_must_match_exactly(self) -> None:
        with self.assertRaises(HTTPException) as context:
            ProductDeletionService._require_confirmation("delete", "DELETE", "request-1")
        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail["code"], "DELETE_CONFIRMATION_REQUIRED")

    def _assessment(self, counts: dict[str, int]) -> dict:
        service = ProductDeletionService(DeleteDb())
        product, owner = _product_fixture(), _owner_fixture()
        product.store_id = owner.store_id
        service._counts = lambda *_: counts  # type: ignore[method-assign]
        service._reference_store_ids = lambda *_: {owner.store_id}  # type: ignore[method-assign]
        return service._assessment(product, owner.store_id)

    def test_zero_stock_inventory_only_history_is_eligible(self) -> None:
        assessment = self._assessment(_counts(inventory_transactions=3))
        self.assertIsNone(assessment["reason"])
        self.assertIsNone(assessment["code"])

    def test_sale_dependency_is_blocked(self) -> None:
        self.assertEqual(self._assessment(_counts(sale_items=1))["code"], "PRODUCT_HAS_SALE_DEPENDENCY")

    def test_purchase_dependency_is_blocked(self) -> None:
        self.assertEqual(self._assessment(_counts(purchase_items=1))["code"], "PRODUCT_HAS_PURCHASE_DEPENDENCY")

    def test_stock_is_blocked(self) -> None:
        self.assertEqual(self._assessment(_counts(physical_stock=1))["code"], "PRODUCT_HAS_STOCK")

    def test_active_cost_lot_pieces_are_blocked(self) -> None:
        self.assertEqual(self._assessment(_counts(active_cost_lot_pieces=1))["code"], "PRODUCT_HAS_ACTIVE_COST_LOTS")

    def test_check_classifies_inventory_only_history_as_deletable(self) -> None:
        service, product, owner = ProductDeletionService(DeleteDb()), _product_fixture(), _owner_fixture()
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": _counts(inventory_transactions=2)}  # type: ignore[method-assign]
        result = service.check([product.id], owner, "request-check")
        self.assertEqual(result["deletable"][0]["classification"], "ZERO_STOCK_INVENTORY_ONLY")
        self.assertEqual(result["deletable"][0]["references"]["inventory_transactions"], 2)

    @patch("app.services.product_deletion_service.DestructiveActionService")
    def test_eligible_product_deletes_after_audited_idempotent_confirmation(self, destructive_cls: Mock) -> None:
        db, service, product, user = DeleteDb(), ProductDeletionService(DeleteDb()), _product_fixture(), _owner_fixture()
        service.db = db
        destructive = destructive_cls.return_value
        destructive._idempotent.return_value = None
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": _counts(inventory_transactions=2)}  # type: ignore[method-assign]
        service._counts = lambda *_args: _counts(inventory_transactions=2)  # type: ignore[method-assign]
        service._purge_inventory_only_dependencies = Mock()  # type: ignore[method-assign]
        service._audit = Mock()  # type: ignore[method-assign]

        result = service.permanently_delete([product.id], "DELETE", "owner-password", "stable-key", user, "request-2")

        self.assertTrue(db.committed)
        self.assertEqual(db.deleted, [product])
        self.assertEqual(result["deleted"][0]["product_name"], product.name)
        service._purge_inventory_only_dependencies.assert_called_once_with(product)  # type: ignore[attr-defined]
        destructive._verify_password.assert_called_once_with("owner-password", user, "request-2", None)
        destructive._store_idempotent.assert_called_once()

    @patch("app.services.product_deletion_service.DestructiveActionService")
    def test_same_idempotency_key_has_no_second_destructive_effect(self, destructive_cls: Mock) -> None:
        service, product, user = ProductDeletionService(DeleteDb()), _product_fixture(), _owner_fixture()
        destructive_cls.return_value._idempotent.return_value = {"deleted": [{"product_id": str(product.id)}], "blocked": [], "request_id": "first"}
        service._locked_products = Mock()  # type: ignore[method-assign]
        result = service.permanently_delete([product.id], "DELETE", "owner-password", "same-key", user, "retry")
        self.assertTrue(result["already_completed"])
        service._locked_products.assert_not_called()  # type: ignore[attr-defined]
        destructive_cls.return_value._verify_password.assert_not_called()

    @patch("app.services.product_deletion_service.DestructiveActionService")
    def test_batch_with_eligible_and_blocked_products_is_atomic(self, destructive_cls: Mock) -> None:
        db, service, eligible, blocked, user = DeleteDb(), ProductDeletionService(DeleteDb()), _product_fixture("Eligible"), _product_fixture("Blocked"), _owner_fixture()
        service.db = db
        destructive_cls.return_value._idempotent.return_value = None
        service._locked_products = lambda *_args, **_kwargs: [eligible, blocked]  # type: ignore[method-assign]
        service._assessment = lambda product, *_args, **_kwargs: {"reason": None, "code": None, "references": _counts()} if product is eligible else {"reason": "Blocked has 1 sale dependency record(s) and cannot be permanently deleted.", "code": "PRODUCT_HAS_SALE_DEPENDENCY", "references": _counts(sale_items=1)}  # type: ignore[method-assign]
        service._audit_blocked = Mock()  # type: ignore[method-assign]
        with self.assertRaises(HTTPException) as context:
            service.permanently_delete([eligible.id, blocked.id], "DELETE", "owner-password", "batch-key", user, "request-batch")
        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(db.deleted, [])
        self.assertTrue(db.committed)

    def test_deletion_audit_snapshot_contains_prices_variants_and_inventory_summary(self) -> None:
        db, service, product, user = DeleteDb(), ProductDeletionService(DeleteDb()), _product_fixture(variants=2), _owner_fixture()
        service.db = db
        service._deletion_snapshot = lambda *_: {"purchase_price": "100", "selling_price": "150", "variants": [{"size": "M"}], "barcode_mappings": [{"barcode": "RFTEST001"}], "inventory_movement_summary": [{"movement_type": "OPENING_STOCK", "count": 1, "quantity_total": 0}]}  # type: ignore[method-assign]
        service._audit(product, user, "request-audit", "PRODUCT_WRONG_ENTRY_PERMANENTLY_DELETED", "WRONG_ENTRY_PURGE", "reason", _counts())
        audit = db.added[0]
        self.assertEqual(audit.event_type, "PRODUCT_WRONG_ENTRY_PERMANENTLY_DELETED")
        self.assertIn("barcode_mappings", audit.product_snapshot)
        self.assertIn("inventory_movement_summary", audit.product_snapshot)

    def test_shared_barcode_keeps_surviving_target_and_rehomes_primary_mapping(self) -> None:
        product, surviving_product = _product_fixture(), _product_fixture("Surviving")
        removed_variant, surviving_variant = product.variants[0], surviving_product.variants[0]
        mapping = SimpleNamespace(id=uuid4(), product_id=product.id, product_variant_id=removed_variant.id)
        db = BarcodeCleanupDb([mapping], [SimpleNamespace(product_variant_id=surviving_variant.id)], surviving_variant)
        ProductDeletionService(db)._purge_inventory_only_dependencies(product)
        self.assertEqual(mapping.product_id, surviving_product.id)
        self.assertEqual(mapping.product_variant_id, surviving_variant.id)
        self.assertNotIn(mapping, db.deleted)
        self.assertIn(ProductBarcodeVariantTarget, db.bulk_deletes)

    def test_unique_barcode_is_removed_with_its_deleted_product(self) -> None:
        product, variant = _product_fixture(), None
        variant = product.variants[0]
        mapping = SimpleNamespace(id=uuid4(), product_id=product.id, product_variant_id=variant.id)
        db = BarcodeCleanupDb([mapping], [])
        ProductDeletionService(db)._purge_inventory_only_dependencies(product)
        self.assertIn(mapping, db.deleted)

    @patch("app.services.product_deletion_service.DestructiveActionService")
    def test_multiple_zero_stock_variants_are_purged_atomically(self, destructive_cls: Mock) -> None:
        db, service, product, user = DeleteDb(), ProductDeletionService(DeleteDb()), _product_fixture(variants=3), _owner_fixture()
        service.db = db
        destructive_cls.return_value._idempotent.return_value = None
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": _counts(variants=3)}  # type: ignore[method-assign]
        service._counts = lambda *_args: _counts(variants=3)  # type: ignore[method-assign]
        service._purge_inventory_only_dependencies = Mock()  # type: ignore[method-assign]
        service._audit = Mock()  # type: ignore[method-assign]
        service.permanently_delete([product.id], "DELETE", "owner-password", "variant-key", user, "request-variants")
        service._purge_inventory_only_dependencies.assert_called_once_with(product)  # type: ignore[attr-defined]
        self.assertEqual(len(product.variants), 3)

    @patch("app.services.product_deletion_service.DestructiveActionService")
    def test_delete_rolls_back_when_any_product_delete_fails(self, destructive_cls: Mock) -> None:
        db, service, product = DeleteDb(fail_delete=True), ProductDeletionService(DeleteDb(fail_delete=True)), _product_fixture()
        service.db = db
        destructive_cls.return_value._idempotent.return_value = None
        service._locked_products = lambda *_args, **_kwargs: [product]  # type: ignore[method-assign]
        service._assessment = lambda *_args, **_kwargs: {"reason": None, "code": None, "references": _counts()}  # type: ignore[method-assign]
        service._counts = lambda *_args: _counts()  # type: ignore[method-assign]
        service._purge_inventory_only_dependencies = Mock()  # type: ignore[method-assign]
        service._audit = Mock()  # type: ignore[method-assign]
        with self.assertRaises(RuntimeError):
            service.permanently_delete([product.id], "DELETE", "owner-password", "rollback-key", _owner_fixture(), "request-3")
        self.assertTrue(db.rolled_back)

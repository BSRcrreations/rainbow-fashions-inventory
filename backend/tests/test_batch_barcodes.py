from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.product_barcode import ProductBarcode
from app.models.product_variant import ProductVariant
from app.models.enums import StockScanMode, StockScanStatus
from app.schemas.stock_scan import BatchBarcodeRequest, StockScanConfirmRequest
from app.services.stock_scan_service import StockScanService


def payload(*barcodes: str) -> BatchBarcodeRequest:
    return BatchBarcodeRequest(product_variant_id=uuid4(), barcodes=list(barcodes))


def test_batch_preserves_barcode_strings_and_leading_zeroes():
    request = payload("0000123456789", "RF-PIECE-2")

    assert request.barcodes == ["0000123456789", "RF-PIECE-2"]


def test_batch_accepts_repeated_manufacturer_barcode_values_as_individual_scans():
    request = payload("0001", "0001", "0001", "0001", "0001")

    assert request.barcodes == ["0001", "0001", "0001", "0001", "0001"]


def test_batch_creates_one_mapping_and_one_draft_piece_per_barcode():
    store_id = uuid4()
    session = SimpleNamespace(id=uuid4())
    variant = SimpleNamespace(id=uuid4(), product_id=uuid4(), mrp=Decimal("549"), selling_price=Decimal("540"), last_purchase_cost=Decimal("250"))
    db = MagicMock()
    service = StockScanService(db)
    service._store_id = MagicMock(return_value=store_id)
    service._editable_session = MagicMock(return_value=session)
    service._variant_for_store = MagicMock(return_value=variant)
    service._validate_barcode = MagicMock()
    service._barcode_mapping = MagicMock(return_value=None)
    service._add_mapping_to_session = MagicMock()
    service.get_session = MagicMock(return_value=session)
    user = SimpleNamespace(id=uuid4(), store_id=store_id)

    service.batch_barcodes(session.id, BatchBarcodeRequest(product_variant_id=variant.id, barcodes=["RF-1", "RF-2", "RF-3"]), user)

    mappings = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], ProductBarcode)]
    assert [mapping.barcode for mapping in mappings] == ["RF-1", "RF-2", "RF-3"]
    assert all(mapping.product_variant_id == variant.id for mapping in mappings)
    assert service._add_mapping_to_session.call_count == 3
    db.commit.assert_called_once()


def test_batch_rejects_a_barcode_owned_by_another_variant_and_rolls_back():
    store_id = uuid4()
    session = SimpleNamespace(id=uuid4())
    variant = SimpleNamespace(id=uuid4(), product_id=uuid4(), mrp=None, selling_price=Decimal("1"), last_purchase_cost=Decimal("0"))
    db = MagicMock()
    service = StockScanService(db)
    service._store_id = MagicMock(return_value=store_id)
    service._editable_session = MagicMock(return_value=session)
    service._variant_for_store = MagicMock(return_value=variant)
    service._validate_barcode = MagicMock()
    service._barcode_mapping = MagicMock(return_value=SimpleNamespace(product_variant_id=uuid4()))
    user = SimpleNamespace(id=uuid4(), store_id=store_id)

    with pytest.raises(HTTPException) as error:
        service.batch_barcodes(session.id, BatchBarcodeRequest(product_variant_id=variant.id, barcodes=["RF-OTHER"]), user)

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "BARCODE_VARIANT_CONFLICT"
    assert error.value.detail["message"] == "This barcode is assigned to another product variant."
    assert error.value.detail["retryable"] is False
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_repeated_scan_increments_one_existing_session_row_without_changing_stock():
    store_id = uuid4()
    session = SimpleNamespace(id=uuid4(), status=None, mode=StockScanMode.PHYSICAL_COUNT)
    variant = SimpleNamespace(id=uuid4(), product_id=uuid4(), current_stock=6)
    mapping = SimpleNamespace(id=uuid4(), barcode="8906058070526", base_unit_conversion=1)
    item = SimpleNamespace(scanned_quantity=0, package_quantity=1, expected_quantity=0, unit_cost=None, condition=None, base_quantity=0, difference_quantity=None, last_scanned_at=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = item
    service = StockScanService(db)
    service._expected_quantity = MagicMock(return_value=0)

    for _ in range(5):
        service._add_mapping_to_session(session, mapping, variant, 1, Decimal("250"), "SELLABLE")

    assert item.scanned_quantity == 5
    assert item.base_quantity == 5
    assert variant.current_stock == 6
    assert db.add.call_count == 0


def test_repeated_scan_uses_a_locked_session_row_to_avoid_lost_quantity():
    source = __import__("inspect").getsource(StockScanService._add_mapping_to_session)

    assert ".with_for_update()" in source


def test_confirmation_is_idempotent_after_it_has_already_applied_stock():
    store_id = uuid4()
    session = SimpleNamespace(id=uuid4(), store_id=store_id, status=StockScanStatus.CONFIRMED)
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = session
    service = StockScanService(db)
    service._store_id = MagicMock(return_value=store_id)
    service.get_session = MagicMock(return_value=session)

    result = service.confirm(session.id, StockScanConfirmRequest(), SimpleNamespace(store_id=store_id))

    assert result is session
    service.get_session.assert_called_once_with(session.id, ANY)


def test_existing_variant_lock_targets_only_the_variant_row():
    db = MagicMock()
    service = StockScanService(db)
    variant_id, store_id = uuid4(), uuid4()
    locked_query = db.query.return_value.join.return_value.options.return_value.filter.return_value
    locked_query.with_for_update.return_value.first.return_value = SimpleNamespace(id=variant_id)

    service._variant_for_store(variant_id, store_id, lock=True)

    locked_query.with_for_update.assert_called_once_with(of=ProductVariant)

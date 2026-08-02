from __future__ import annotations

from decimal import Decimal
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.enums import StockScanStatus
from app.models.product_barcode import ProductBarcode
from app.schemas.stock_scan import BarcodeProductOnboarding
from app.services.stock_scan_service import StockScanService


def existing_payload(**overrides: object) -> BarcodeProductOnboarding:
    values: dict[str, object] = {
        "session_id": uuid4(),
        "action": "EXISTING_VARIANT",
        "barcode": "0012345678905",
        "product_variant_id": uuid4(),
        "quantity": 2,
    }
    values.update(overrides)
    return BarcodeProductOnboarding(**values)


def configured_service(status: StockScanStatus = StockScanStatus.IN_PROGRESS):
    store_id = uuid4()
    session = SimpleNamespace(id=uuid4(), store_id=store_id, status=status, mode=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = session
    service = StockScanService(db)
    service._store_id = MagicMock(return_value=store_id)
    service._validate_barcode = MagicMock()
    service.get_session = MagicMock(return_value=SimpleNamespace(id=session.id))
    return service, db, session, store_id


def active_variant(store_id):
    return SimpleNamespace(
        id=uuid4(),
        store_id=store_id,
        product_id=uuid4(),
        is_active=True,
        product=SimpleNamespace(is_active=True),
        mrp=Decimal("499"),
        selling_price=Decimal("449"),
        last_purchase_cost=Decimal("250"),
        average_cost=Decimal("250"),
        current_stock=9,
    )


def user(store_id):
    return SimpleNamespace(id=uuid4(), store_id=store_id)


def test_existing_variant_payload_allows_the_minimal_assignment_request():
    payload = existing_payload()

    assert payload.purchase_cost is None
    assert payload.selling_price is None
    assert payload.product_name is None


def test_new_variant_still_requires_prices():
    with pytest.raises(ValidationError):
        BarcodeProductOnboarding(
            session_id=uuid4(),
            action="NEW_VARIANT",
            barcode="RF-NEW-VARIANT",
            existing_product_id=uuid4(),
        )


def test_existing_variant_creates_a_mapping_and_adds_only_the_draft_line():
    service, db, _, store_id = configured_service()
    variant = active_variant(store_id)
    payload = existing_payload(product_variant_id=variant.id)
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=None)
    service._add_mapping_to_session = MagicMock()

    result = service.onboard_product(payload, user(store_id))

    mapping = next(item.args[0] for item in db.add.call_args_list if isinstance(item.args[0], ProductBarcode))
    assert mapping.product_variant_id == variant.id
    assert mapping.barcode == payload.barcode
    service._add_mapping_to_session.assert_called_once()
    assert service._add_mapping_to_session.call_args.args[3] == payload.quantity
    assert result.id


def test_existing_variant_does_not_change_variant_prices_costs_or_stock():
    service, _, _, store_id = configured_service()
    variant = active_variant(store_id)
    before = (variant.mrp, variant.selling_price, variant.last_purchase_cost, variant.average_cost, variant.current_stock)
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=None)
    service._add_mapping_to_session = MagicMock()

    service.onboard_product(existing_payload(product_variant_id=variant.id), user(store_id))

    assert (variant.mrp, variant.selling_price, variant.last_purchase_cost, variant.average_cost, variant.current_stock) == before


def test_existing_variant_reuses_its_current_mapping_and_adds_the_scan():
    service, db, _, store_id = configured_service()
    variant = active_variant(store_id)
    mapping = SimpleNamespace(product_variant_id=variant.id, active=True, barcode="0012345678905")
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=mapping)
    service._add_mapping_to_session = MagicMock()

    service.onboard_product(existing_payload(product_variant_id=variant.id), user(store_id))

    service._add_mapping_to_session.assert_called_once()
    assert not any(isinstance(item.args[0], ProductBarcode) for item in db.add.call_args_list)


def test_existing_variant_rejects_a_barcode_mapped_to_a_different_variant():
    service, _, _, store_id = configured_service()
    variant = active_variant(store_id)
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=SimpleNamespace(product_variant_id=uuid4(), active=True))

    with pytest.raises(HTTPException, match="already assigned to another product variant") as error:
        service.onboard_product(existing_payload(product_variant_id=variant.id), user(store_id))

    assert error.value.status_code == 409


def test_existing_variant_rejects_a_confirmed_session_without_mutating_it():
    service, db, _, store_id = configured_service(StockScanStatus.CONFIRMED)

    with pytest.raises(HTTPException, match="confirmed and cannot be changed") as error:
        service.onboard_product(existing_payload(), user(store_id))

    assert error.value.status_code == 409
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_existing_variant_lookup_is_authoritatively_scoped_to_the_current_store():
    service, _, _, store_id = configured_service()
    variant = active_variant(store_id)
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=None)
    service._add_mapping_to_session = MagicMock()
    payload = existing_payload(product_variant_id=variant.id)

    service.onboard_product(payload, user(store_id))

    service._variant_for_store.assert_called_once_with(payload.product_variant_id, store_id, lock=True)


def test_existing_variant_uses_existing_cost_for_the_draft_not_frontend_input():
    service, _, _, store_id = configured_service()
    variant = active_variant(store_id)
    service._variant_for_store = MagicMock(return_value=variant)
    service._barcode_mapping = MagicMock(return_value=None)
    service._add_mapping_to_session = MagicMock()

    service.onboard_product(existing_payload(product_variant_id=variant.id), user(store_id))

    assert service._add_mapping_to_session.call_args.args[4] == Decimal("250")


def test_existing_variant_lookup_requires_active_variant_and_active_product():
    source = inspect.getsource(StockScanService._variant_for_store)

    assert "ProductVariant.store_id == store_id" in source
    assert "ProductVariant.is_active.is_(True)" in source
    assert "Product.is_active.is_(True)" in source


def test_scanning_a_confirmed_session_is_locked_with_the_same_clear_message():
    service, _, session, store_id = configured_service(StockScanStatus.CONFIRMED)
    service.get_session = MagicMock(return_value=session)

    with pytest.raises(HTTPException, match="confirmed and cannot be changed") as error:
        service._editable_session(session.id, user(store_id))

    assert error.value.status_code == 409


def test_existing_variant_payload_does_not_require_optional_metadata():
    payload = existing_payload(size=None, color=None, style_code=None, category_id=None, brand_id=None)

    assert payload.action == "EXISTING_VARIANT"
    assert payload.category_id is None
    assert payload.brand_id is None

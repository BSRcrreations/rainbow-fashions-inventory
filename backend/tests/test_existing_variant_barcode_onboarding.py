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
from app.models.product_barcode import ProductBarcode, ProductBarcodeAudit
from app.models.stock_history import StockHistory
from app.schemas.stock_scan import BarcodeProductOnboarding, BarcodeTransferLineRead, BulkBarcodeTransferRequest
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


def transfer_variant(store_id, product_id, size: str, stock: int):
    return SimpleNamespace(
        id=uuid4(),
        store_id=store_id,
        product_id=product_id,
        size=size,
        color="all",
        style_code="Ankil",
        current_stock=stock,
        average_cost=Decimal("100"),
        product=SimpleNamespace(name="Twin birds ankle", brand=SimpleNamespace(name="Twin birds")),
    )


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


def test_blank_optional_uuid_fields_are_normalized_before_validation():
    payload = BarcodeProductOnboarding(
        session_id=uuid4(),
        action="NEW_VARIANT",
        barcode="RF-NEW-VARIANT",
        existing_product_id=uuid4(),
        product_variant_id="",
        category_id="",
        subcategory_id="",
        brand_id="",
        purchase_cost=Decimal("250"),
        selling_price=Decimal("395"),
    )

    assert payload.product_variant_id is None
    assert payload.category_id is None
    assert payload.subcategory_id is None
    assert payload.brand_id is None


def test_new_variant_does_not_require_client_product_category_or_brand_metadata():
    payload = BarcodeProductOnboarding(
        session_id=uuid4(),
        action="NEW_VARIANT",
        barcode="RF-NEW-VARIANT",
        existing_product_id=uuid4(),
        purchase_cost=Decimal("250"),
        selling_price=Decimal("395"),
        category_id="",
        brand_id="",
    )

    assert payload.category_id is None
    assert payload.brand_id is None


def test_new_product_requires_a_brand_or_unbranded_selection():
    with pytest.raises(ValidationError, match="Select a brand or choose Unbranded") as error:
        BarcodeProductOnboarding(
            session_id=uuid4(),
            action="NEW_PRODUCT",
            barcode="RF-NEW-PRODUCT",
            product_name="Padded Bra",
            category_id=uuid4(),
            brand_id="",
            purchase_cost=Decimal("250"),
            selling_price=Decimal("395"),
        )

    assert error.value.errors()[0]["type"] == "BRAND_REQUIRED"


def test_action_specific_required_ids_use_stable_friendly_validation_codes():
    with pytest.raises(ValidationError) as existing_variant_error:
        BarcodeProductOnboarding(session_id=uuid4(), action="EXISTING_VARIANT", barcode="RF-EXISTING")
    with pytest.raises(ValidationError) as new_variant_error:
        BarcodeProductOnboarding(
            session_id=uuid4(),
            action="NEW_VARIANT",
            barcode="RF-NEW-VARIANT",
            purchase_cost=Decimal("250"),
            selling_price=Decimal("395"),
        )

    assert existing_variant_error.value.errors()[0]["type"] == "EXISTING_VARIANT_REQUIRED"
    assert new_variant_error.value.errors()[0]["type"] == "EXISTING_PRODUCT_REQUIRED"


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


def test_new_variant_blocks_an_exact_duplicate_variant_before_creating_anything():
    service, db, _, store_id = configured_service()
    product = SimpleNamespace(id=uuid4(), store_id=store_id)
    duplicate_variant = SimpleNamespace(id=uuid4())
    payload = BarcodeProductOnboarding(
        session_id=uuid4(),
        action="NEW_VARIANT",
        barcode="RF-NEW-VARIANT",
        existing_product_id=product.id,
        size="34/85 cm",
        color="all",
        style_code="SoftA",
        purchase_cost=Decimal("250"),
        selling_price=Decimal("395"),
    )
    service._barcode_mapping = MagicMock(return_value=None)
    service._product_for_store = MagicMock(return_value=product)
    service._matching_variant_for_payload = MagicMock(return_value=duplicate_variant)
    service._create_variant = MagicMock()

    with pytest.raises(HTTPException) as error:
        service.onboard_product(payload, user(store_id))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "VARIANT_ALREADY_EXISTS"
    service._create_variant.assert_not_called()
    db.add.assert_not_called()


def test_new_variant_uses_the_selected_store_product_without_overwriting_its_hierarchy():
    service, _, _, store_id = configured_service()
    product = SimpleNamespace(
        id=uuid4(),
        store_id=store_id,
        name="Padded Bra",
        category_id=uuid4(),
        subcategory_id=uuid4(),
        brand_id=uuid4(),
    )
    hierarchy_before = (product.name, product.category_id, product.subcategory_id, product.brand_id)
    variant = active_variant(store_id)
    payload = BarcodeProductOnboarding(
        session_id=uuid4(),
        action="NEW_VARIANT",
        barcode="RF-NEW-SIZE",
        existing_product_id=product.id,
        # These deliberately untrusted fields are ignored for NEW_VARIANT.
        category_id=uuid4(),
        brand_id=uuid4(),
        size="36/90 cm",
        color="all",
        style_code="SoftA",
        purchase_cost=Decimal("250"),
        selling_price=Decimal("395"),
    )
    service._barcode_mapping = MagicMock(return_value=None)
    service._product_for_store = MagicMock(return_value=product)
    service._matching_variant_for_payload = MagicMock(return_value=None)
    service._create_variant = MagicMock(return_value=variant)
    service._add_mapping_to_session = MagicMock()

    service.onboard_product(payload, user(store_id))

    service._product_for_store.assert_called_once_with(product.id, store_id, lock=True)
    assert service._create_variant.call_args.args[0] is product
    assert (product.name, product.category_id, product.subcategory_id, product.brand_id) == hierarchy_before


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


def test_confirmed_session_guard_uses_a_stable_error_code_for_all_mutations():
    source = inspect.getsource(StockScanService._editable_session)

    assert '"STOCK_SESSION_CONFIRMED"' in source


def test_existing_variant_payload_does_not_require_optional_metadata():
    payload = existing_payload(size=None, color=None, style_code=None, category_id=None, brand_id=None)

    assert payload.action == "EXISTING_VARIANT"
    assert payload.category_id is None
    assert payload.brand_id is None


def test_bulk_transfer_rejects_duplicate_request_barcodes():
    with pytest.raises(ValidationError, match="Duplicate barcode values"):
        BulkBarcodeTransferRequest(
            barcodes=["8903289095861", "8903289095861"],
            target_product_variant_id=uuid4(),
            reason="Incorrect size assignment: M to S",
            confirmation_phrase="MOVE TO S",
        )


def test_bulk_transfer_preserves_barcode_strings_and_moves_draft_only_without_stock_change():
    service, db, _, store_id = configured_service()
    product_id = uuid4()
    source = transfer_variant(store_id, product_id, "M", 10)
    target = transfer_variant(store_id, product_id, "S", 2)
    line = BarcodeTransferLineRead(
        barcode="08903289095861",
        barcode_id=uuid4(),
        source_variant_id=source.id,
        target_variant_id=target.id,
        draft_session_item_ids=[uuid4()],
    )
    mapping = SimpleNamespace(id=line.barcode_id, store_id=store_id, product_id=product_id, product_variant_id=source.id, barcode=line.barcode, active=True)
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mapping
    service._variant_for_store = MagicMock(return_value=target)
    service._bulk_transfer_plan = MagicMock(return_value=([line], source))
    service._move_draft_scan_items = MagicMock()

    result = service.bulk_transfer_barcodes(
        BulkBarcodeTransferRequest(barcodes=[line.barcode], target_product_variant_id=target.id, reason="Incorrect size assignment: M to S", confirmation_phrase="MOVE TO S"),
        user(store_id),
        "req-1",
    )

    assert result.barcodes == ["08903289095861"]
    assert result.draft_only is True
    assert source.current_stock == 10
    assert target.current_stock == 2
    assert mapping.product_variant_id == target.id
    assert not any(isinstance(call.args[0], StockHistory) for call in db.add.call_args_list)


def test_bulk_transfer_confirmed_rows_create_paired_stock_corrections_and_audit():
    service, db, _, store_id = configured_service()
    product_id = uuid4()
    source = transfer_variant(store_id, product_id, "M", 10)
    target = transfer_variant(store_id, product_id, "S", 2)
    lines = [
        BarcodeTransferLineRead(barcode="8903289095861", barcode_id=uuid4(), source_variant_id=source.id, target_variant_id=target.id, confirmed_quantity=1),
        BarcodeTransferLineRead(barcode="8903289095502", barcode_id=uuid4(), source_variant_id=source.id, target_variant_id=target.id, confirmed_quantity=1),
        BarcodeTransferLineRead(barcode="8903289118621", barcode_id=uuid4(), source_variant_id=source.id, target_variant_id=target.id, confirmed_quantity=1),
        BarcodeTransferLineRead(barcode="8903289110502", barcode_id=uuid4(), source_variant_id=source.id, target_variant_id=target.id, confirmed_quantity=1),
    ]
    mappings = {
        line.barcode_id: SimpleNamespace(id=line.barcode_id, store_id=store_id, product_id=product_id, product_variant_id=source.id, barcode=line.barcode, active=True)
        for line in lines
    }
    db.query.return_value.filter.return_value.with_for_update.return_value.first.side_effect = [mappings[line.barcode_id] for line in lines]
    service._variant_for_store = MagicMock(return_value=target)
    service._bulk_transfer_plan = MagicMock(return_value=(lines, source))
    service._move_draft_scan_items = MagicMock()

    result = service.bulk_transfer_barcodes(
        BulkBarcodeTransferRequest(barcodes=[line.barcode for line in lines], target_product_variant_id=target.id, reason="Incorrect size assignment: M to S", confirmation_phrase="MOVE TO S"),
        user(store_id),
        "req-2",
    )

    histories = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], StockHistory)]
    audits = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], ProductBarcodeAudit)]
    assert source.current_stock == 6
    assert target.current_stock == 6
    assert result.source_stock_delta == -4
    assert result.target_stock_delta == 4
    assert result.net_stock_delta == 0
    assert len(histories) == 2
    assert {history.qty for history in histories} == {4}
    assert len(audits) == 4
    assert audits[0].action == "BARCODE_TRANSFERRED"
    assert audits[0].old_product_variant_id == source.id
    assert audits[0].new_product_variant_id == target.id
    assert audits[0].metadata_json["old_size"] == "M"
    assert audits[0].metadata_json["new_size"] == "S"


def test_bulk_transfer_rolls_back_when_a_mapping_changes_during_execution():
    service, db, _, store_id = configured_service()
    product_id = uuid4()
    source = transfer_variant(store_id, product_id, "M", 10)
    target = transfer_variant(store_id, product_id, "S", 2)
    stale = SimpleNamespace(id=uuid4(), store_id=store_id, product_id=product_id, product_variant_id=uuid4(), barcode="8903289095861", active=True)
    line = BarcodeTransferLineRead(barcode=stale.barcode, barcode_id=stale.id, source_variant_id=source.id, target_variant_id=target.id)
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = stale
    service._variant_for_store = MagicMock(return_value=target)
    service._bulk_transfer_plan = MagicMock(return_value=([line], source))

    with pytest.raises(HTTPException, match="mapping changed"):
        service.bulk_transfer_barcodes(
            BulkBarcodeTransferRequest(barcodes=[line.barcode], target_product_variant_id=target.id, reason="Incorrect size assignment: M to S", confirmation_phrase="MOVE TO S"),
            user(store_id),
            "req-3",
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

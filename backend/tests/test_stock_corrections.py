from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.stock import StockCorrectionCreate
from app.services.stock_service import StockService


def locked_query(result):
    query = MagicMock()
    query.filter.return_value.with_for_update.return_value.first.return_value = result
    return query


def correction_payload(quantity: int = 8) -> StockCorrectionCreate:
    return StockCorrectionCreate(correct_quantity=quantity, reason="DATA_ENTRY_MISTAKE", reference="COUNT-SHEET-1")


def test_correction_appends_a_new_movement_and_preserves_the_original():
    store_id, product_id, transaction_id = uuid4(), uuid4(), uuid4()
    original = SimpleNamespace(id=transaction_id, store_id=store_id, product_id=product_id, product_variant_id=None, after_stock=10, correction_of_id=None, qty=10)
    product = SimpleNamespace(id=product_id, store_id=store_id, current_stock=10)
    inventory = SimpleNamespace(current_stock=10)
    db = MagicMock()
    db.query.side_effect = [locked_query(original), locked_query(product)]
    service = StockService(db)
    service._get_or_create_inventory = MagicMock(return_value=inventory)
    db.refresh.side_effect = lambda movement: setattr(movement, "id", uuid4())
    user = SimpleNamespace(id=uuid4(), store_id=store_id)

    movement = service.correct_transaction(transaction_id, correction_payload(8), user)

    assert original.after_stock == 10
    assert product.current_stock == 8
    assert inventory.current_stock == 8
    assert movement.correction_of_id == transaction_id
    assert movement.qty == 2
    db.commit.assert_called_once()


def test_correction_rejects_a_transaction_outside_the_current_store():
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
    service = StockService(db)
    user = SimpleNamespace(id=uuid4(), store_id=uuid4())

    with pytest.raises(HTTPException) as error:
        service.correct_transaction(uuid4(), correction_payload(), user)

    assert error.value.status_code == 404
    db.commit.assert_not_called()


def test_correction_requires_notes_when_reason_is_other():
    with pytest.raises(ValueError, match="Notes are required"):
        StockCorrectionCreate(correct_quantity=8, reason="OTHER")

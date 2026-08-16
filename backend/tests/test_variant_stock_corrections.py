from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.stock import VariantCorrectionMoveRequest
from app.services.stock_service import StockService


def _variant(stock: int, size: str, product_id=None):
    product_id = product_id or uuid4()
    return SimpleNamespace(
        id=uuid4(), product_id=product_id, store_id=uuid4(), size=size, color="Navy",
        barcode=f"890-{size}", internal_sku=f"LEG-{size}", current_stock=stock,
        average_cost=Decimal("100"), last_purchase_cost=Decimal("100"), is_active=True,
        product=SimpleNamespace(id=product_id, name="Full Leggings", purchase_price=Decimal("100")),
    )


def test_variant_correction_preview_calculates_full_and_partial_moves_without_mutation():
    source, destination = _variant(5, "L"), _variant(0, "XL")
    destination.product_id = source.product_id
    destination.product.id = source.product_id
    payload = VariantCorrectionMoveRequest(source_variant_id=source.id, destination_variant_id=destination.id, quantity=2, reason="WRONG_SIZE_ENTERED")

    response = StockService(MagicMock())._variant_correction_response(source, destination, payload, "request-1")

    assert response["source"]["before_stock"] == 5
    assert response["source"]["after_stock"] == 3
    assert response["destination"]["before_stock"] == 0
    assert response["destination"]["after_stock"] == 2
    assert source.current_stock == 5
    assert destination.current_stock == 0


def test_variant_correction_supports_custom_and_numeric_sizes():
    source, destination = _variant(5, "Free Size"), _variant(0, "32")
    destination.product_id = source.product_id
    destination.product.id = source.product_id
    payload = VariantCorrectionMoveRequest(source_variant_id=source.id, destination_variant_id=destination.id, quantity=1, reason="DATA_ENTRY_MISTAKE")

    response = StockService(MagicMock())._variant_correction_response(source, destination, payload, "request-1")

    assert response["source"]["size"] == "Free Size"
    assert response["destination"]["size"] == "32"


def test_variant_correction_preview_blocks_insufficient_stock():
    source, destination = _variant(1, "L"), _variant(0, "XL")
    destination.product_id = source.product_id
    destination.product.id = source.product_id
    payload = VariantCorrectionMoveRequest(source_variant_id=source.id, destination_variant_id=destination.id, quantity=2, reason="WRONG_SIZE_ENTERED")

    with pytest.raises(HTTPException) as error:
        StockService(MagicMock())._variant_correction_response(source, destination, payload, "request-1")

    assert error.value.status_code == 409
    assert "Only 1 pieces are available" in str(error.value.detail)


def test_variant_correction_schema_blocks_same_variant_and_requires_other_notes():
    variant_id = uuid4()
    with pytest.raises(ValueError, match="different variants"):
        VariantCorrectionMoveRequest(source_variant_id=variant_id, destination_variant_id=variant_id, quantity=1, reason="TEST_DATA")
    with pytest.raises(ValueError, match="Notes are required"):
        VariantCorrectionMoveRequest(source_variant_id=uuid4(), destination_variant_id=uuid4(), quantity=1, reason="OTHER")


def test_variant_correction_hash_prevents_idempotency_key_reuse_for_different_moves():
    source, destination = uuid4(), uuid4()
    first = VariantCorrectionMoveRequest(source_variant_id=source, destination_variant_id=destination, quantity=1, reason="TEST_DATA")
    second = VariantCorrectionMoveRequest(source_variant_id=source, destination_variant_id=destination, quantity=2, reason="TEST_DATA")

    assert StockService._variant_correction_hash(first) != StockService._variant_correction_hash(second)

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.models.enums import StockMovementType, UserRole
from app.models.stock_history import StockHistory
from app.schemas.stock import StockResetConfirmRequest, StockResetPreviewRequest
from app.services.stock_service import StockService


CONFIRMATION = "This will set the selected existing stock quantities to zero. Products, variants and barcodes will remain available."


def _user(store_id):
    return SimpleNamespace(id=uuid4(), store_id=store_id, role=UserRole.OWNER)


def _variant(stock: int = 8):
    store_id, product_id = uuid4(), uuid4()
    product = SimpleNamespace(
        id=product_id,
        name="Full Leggings",
        purchase_price=Decimal("386.22"),
        brand=SimpleNamespace(name="Prisma"),
        category=SimpleNamespace(name="Leggings"),
    )
    return SimpleNamespace(
        id=uuid4(),
        product_id=product_id,
        store_id=store_id,
        size="XL",
        color="Assorted",
        barcode="8906058070526",
        internal_sku="FULL-XL-549-A",
        average_cost=Decimal("386.22"),
        last_purchase_cost=Decimal("386.22"),
        current_stock=stock,
        product=product,
    )


def test_reset_preview_reports_server_calculated_reversal_values():
    service = StockService(MagicMock())
    variant = _variant(8)

    response = service._reset_response([variant], "request-1", [])

    assert response["total_products"] == 1
    assert response["total_variants"] == 1
    assert response["total_pieces"] == 8
    assert response["variants"][0]["current_stock"] == 8
    assert response["variants"][0]["reset_quantity"] == -8
    assert response["variants"][0]["resulting_stock"] == 0
    assert response["variants"][0]["barcode"] == "8906058070526"


def test_reset_exact_variant_to_zero_preserves_variant_and_barcode():
    db = MagicMock()
    service = StockService(db)
    variant = _variant(8)
    user = _user(variant.store_id)
    payload = StockResetConfirmRequest(scope="SELECTED_VARIANTS", variant_ids=[variant.id], confirmation=CONFIRMATION)
    service._idempotent_reset = MagicMock(return_value=None)
    service._verify_owner_reset_password = MagicMock()
    service._reset_variants = MagicMock(return_value=[variant])
    service._zero_variant_cost_lots = MagicMock()
    service._sync_product_stock = MagicMock()
    service._store_idempotent_reset = MagicMock()
    service._audit = MagicMock()
    db.flush.side_effect = lambda: setattr(db.add.call_args.args[0], "id", uuid4()) if isinstance(db.add.call_args.args[0], StockHistory) else None

    response = service.reset_existing_stock(payload, user, "idem-1", "request-1")

    movements = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], StockHistory)]
    assert variant.current_stock == 0
    assert variant.barcode == "8906058070526"
    assert movements[0].product_variant_id == variant.id
    assert movements[0].movement_type == StockMovementType.STOCK_RESET_OUT
    assert movements[0].qty == 8
    assert movements[0].before_stock == 8
    assert movements[0].after_stock == 0
    assert response["variants"][0]["current_stock"] == 8
    assert response["variants"][0]["reset_quantity"] == -8
    db.commit.assert_called_once()


def test_idempotent_repeated_reset_returns_cached_response_without_mutating_stock():
    db = MagicMock()
    service = StockService(db)
    variant = _variant(8)
    user = _user(variant.store_id)
    payload = StockResetConfirmRequest(scope="SELECTED_VARIANTS", variant_ids=[variant.id], confirmation=CONFIRMATION)
    cached = {"variants": [], "total_products": 0, "total_variants": 0, "total_pieces": 0, "total_inventory_value": "0", "request_id": "request-1", "stock_history_ids": [], "already_completed": False}
    service._idempotent_reset = MagicMock(return_value=cached)

    response = service.reset_existing_stock(payload, user, "idem-1", "request-1")

    assert response["already_completed"] is True
    assert variant.current_stock == 8
    db.add.assert_not_called()
    db.commit.assert_not_called()

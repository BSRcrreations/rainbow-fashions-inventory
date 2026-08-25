from decimal import Decimal
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.product_variant import InventoryCostLot
from app.services.dashboard_service import DashboardService
from app.services.inventory_valuation_service import InventoryValuationService
from app.services.sale_service import SaleService


def test_current_value_uses_multiple_active_cost_lots_not_product_purchase_price() -> None:
    engine = create_engine("sqlite://")
    InventoryCostLot.__table__.create(engine)
    store_id, other_store_id, first_variant, second_variant = uuid4(), uuid4(), uuid4(), uuid4()
    with Session(engine) as db:
        db.add_all(
            [
                InventoryCostLot(store_id=store_id, product_variant_id=first_variant, received_quantity=4, remaining_quantity=4, unit_purchase_cost=Decimal("100.00"), effective_unit_cost=Decimal("100.00")),
                InventoryCostLot(store_id=store_id, product_variant_id=second_variant, received_quantity=3, remaining_quantity=3, unit_purchase_cost=Decimal("245.00"), effective_unit_cost=Decimal("245.00")),
                InventoryCostLot(store_id=store_id, product_variant_id=second_variant, received_quantity=9, remaining_quantity=0, unit_purchase_cost=Decimal("999.00"), effective_unit_cost=Decimal("999.00")),
                InventoryCostLot(store_id=other_store_id, product_variant_id=uuid4(), received_quantity=2, remaining_quantity=2, unit_purchase_cost=Decimal("500.00"), effective_unit_cost=Decimal("500.00")),
            ]
        )
        db.commit()

        value = InventoryValuationService(db).current_value(store_id)

    assert value == Decimal("1135.00")


def test_dashboard_delegates_inventory_value_to_the_shared_cost_lot_service() -> None:
    sales_source = inspect.getsource(SaleService.dashboard)
    summary_source = inspect.getsource(DashboardService.summary)

    assert "InventoryValuationService(self.db).current_value(store_id)" in sales_source
    assert "InventoryValuationService(self.db).current_value(current_user.store_id)" in summary_source
    assert "Product.purchase_price * Product.current_stock" not in sales_source
    assert "Product.current_stock * Product.purchase_price" not in summary_source


def test_stock_endpoint_delegates_to_the_shared_authoritative_valuation_service() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = Decimal("935.00")
    user = SimpleNamespace(store_id=uuid4())

    from app.services.stock_service import StockService

    assert StockService(db).inventory_valuation(user) == {"inventory_value": Decimal("935.00")}

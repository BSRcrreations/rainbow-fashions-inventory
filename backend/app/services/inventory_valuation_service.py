from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product_variant import InventoryCostLot


class InventoryValuationService:
    """Single authoritative current-inventory valuation from active cost lots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def current_value(self, store_id: UUID) -> Decimal:
        value = (
            self.db.query(
                func.coalesce(
                    func.sum(InventoryCostLot.remaining_quantity * InventoryCostLot.effective_unit_cost),
                    0,
                )
            )
            .filter(
                InventoryCostLot.store_id == store_id,
                InventoryCostLot.remaining_quantity > 0,
            )
            .scalar()
        )
        return Decimal(value or 0)

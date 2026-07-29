from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import joinedload

from app.models.enums import StockMovementType
from app.models.stock_history import StockHistory
from app.repositories.base import BaseRepository


class StockHistoryRepository(BaseRepository[StockHistory]):
    model = StockHistory

    def list_recent(
        self,
        skip: int = 0,
        limit: int = 100,
        product_id: Optional[UUID] = None,
        movement_type: Optional[StockMovementType] = None,
        store_id: Optional[UUID] = None,
    ) -> list[StockHistory]:
        query = self.db.query(StockHistory).options(joinedload(StockHistory.product), joinedload(StockHistory.created_by_user))
        if product_id:
            query = query.filter(StockHistory.product_id == product_id)
        if movement_type:
            query = query.filter(StockHistory.movement_type == movement_type)
        if store_id:
            query = query.filter(StockHistory.store_id == store_id)
        return query.order_by(StockHistory.movement_date.desc()).offset(skip).limit(limit).all()

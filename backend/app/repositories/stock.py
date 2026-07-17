from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import joinedload

from app.models.stock_history import StockHistory
from app.repositories.base import BaseRepository


class StockHistoryRepository(BaseRepository[StockHistory]):
    model = StockHistory

    def list_recent(
        self,
        skip: int = 0,
        limit: int = 100,
        movement_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[StockHistory]:
        query = self.db.query(StockHistory).options(joinedload(StockHistory.product))
        if movement_type:
            query = query.filter(StockHistory.movement_type == movement_type)
        if from_date:
            query = query.filter(StockHistory.movement_date >= from_date)
        if to_date:
            query = query.filter(StockHistory.movement_date <= to_date)
        return (
            query.order_by(StockHistory.movement_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

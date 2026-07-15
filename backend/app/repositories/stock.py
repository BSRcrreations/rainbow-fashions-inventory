from __future__ import annotations

from app.models.stock_history import StockHistory
from app.repositories.base import BaseRepository


class StockHistoryRepository(BaseRepository[StockHistory]):
    model = StockHistory

    def list_recent(self, skip: int = 0, limit: int = 100) -> list[StockHistory]:
        return (
            self.db.query(StockHistory)
            .order_by(StockHistory.movement_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import joinedload

from app.models.purchase import Purchase
from app.repositories.base import BaseRepository


class PurchaseRepository(BaseRepository[Purchase]):
    model = Purchase

    def list_recent(self, skip: int = 0, limit: int = 50) -> list[Purchase]:
        return (
            self.db.query(Purchase)
            .options(joinedload(Purchase.items), joinedload(Purchase.uploaded_file))
            .order_by(Purchase.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_items(self, purchase_id: UUID) -> Optional[Purchase]:
        return (
            self.db.query(Purchase)
            .options(joinedload(Purchase.items), joinedload(Purchase.uploaded_file))
            .filter(Purchase.id == purchase_id)
            .first()
        )

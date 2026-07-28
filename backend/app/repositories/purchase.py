from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models.purchase import Purchase
from app.repositories.base import BaseRepository


class PurchaseRepository(BaseRepository[Purchase]):
    model = Purchase

    def list_recent(self, store_id: UUID, skip: int = 0, limit: int = 50, status_filter: Optional[str] = None) -> list[Purchase]:
        query = (
            self.db.query(Purchase)
            .options(joinedload(Purchase.items), joinedload(Purchase.uploaded_file), joinedload(Purchase.supplier))
            .filter(Purchase.store_id == store_id)
        )
        if status_filter == "REVIEW_REQUIRED":
            query = query.filter(Purchase.ai_processing_status.ilike("%REVIEW_REQUIRED%"))
        elif status_filter == "FAILED":
            query = query.filter(Purchase.ai_processing_status == "FAILED")
        elif status_filter:
            query = query.filter(Purchase.status == status_filter)
        return query.order_by(Purchase.created_at.desc()).offset(skip).limit(limit).all()

    def get_with_items(self, purchase_id: UUID, store_id: UUID) -> Optional[Purchase]:
        return (
            self.db.query(Purchase)
            .options(joinedload(Purchase.items), joinedload(Purchase.uploaded_file), joinedload(Purchase.supplier))
            .filter(Purchase.id == purchase_id, Purchase.store_id == store_id)
            .first()
        )

    def find_duplicate(self, store_id: UUID, supplier_name: Optional[str], invoice_number: Optional[str], invoice_date, total_amount, exclude_id: Optional[UUID] = None) -> Optional[Purchase]:
        if not invoice_number:
            return None
        query = self.db.query(Purchase).filter(Purchase.store_id == store_id, Purchase.invoice_number == invoice_number, Purchase.invoice_date == invoice_date, Purchase.total_amount == total_amount)
        if supplier_name:
            query = query.filter(Purchase.supplier_name == supplier_name)
        if exclude_id:
            query = query.filter(Purchase.id != exclude_id)
        return query.first()

    def find_duplicate_invoice(self, store_id: UUID, supplier_id: Optional[UUID], supplier_name: Optional[str], invoice_number: Optional[str], exclude_id: Optional[UUID] = None) -> Optional[Purchase]:
        if not invoice_number or not invoice_number.strip():
            return None
        query = self.db.query(Purchase).filter(
            Purchase.store_id == store_id,
            func.lower(Purchase.invoice_number) == invoice_number.strip().casefold(),
        )
        if supplier_id:
            query = query.filter(Purchase.supplier_id == supplier_id)
        elif supplier_name:
            query = query.filter(Purchase.supplier_id.is_(None), func.lower(Purchase.supplier_name) == supplier_name.strip().casefold())
        if exclude_id:
            query = query.filter(Purchase.id != exclude_id)
        return query.first()

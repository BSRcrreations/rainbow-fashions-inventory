from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models.sale import Sale, SaleAudit, SaleReturn
from app.models.user import User
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    model = Sale

    def get_detail(self, sale_id: UUID, store_id: UUID) -> Optional[Sale]:
        return (
            self.db.query(Sale)
            .options(joinedload(Sale.items), joinedload(Sale.cashier))
            .filter(Sale.id == sale_id, Sale.store_id == store_id)
            .first()
        )

    def get_by_invoice(self, invoice_number: str, store_id: UUID) -> Optional[Sale]:
        return self.db.query(Sale).filter(Sale.invoice_number == invoice_number, Sale.store_id == store_id).first()

    def list_paginated(
        self,
        page: int,
        page_size: int,
        search: Optional[str],
        payment_mode: Optional[str],
        start_at: Optional[datetime],
        end_at: Optional[datetime],
        invoice_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        cashier_name: Optional[str] = None,
        store_id: Optional[UUID] = None,
        sort: str = "newest",
    ) -> tuple[list[Sale], int]:
        query = self.db.query(Sale).outerjoin(Sale.cashier).options(joinedload(Sale.cashier), joinedload(Sale.items))
        if store_id is not None:
            query = query.filter(Sale.store_id == store_id)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Sale.invoice_number.ilike(pattern),
                    Sale.customer_name.ilike(pattern),
                    Sale.payment_mode.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )
        if payment_mode:
            query = query.filter(Sale.payment_mode == payment_mode)
        if invoice_number:
            query = query.filter(Sale.invoice_number.ilike(f"%{invoice_number.strip()}%"))
        if customer_name:
            query = query.filter(Sale.customer_name.ilike(f"%{customer_name.strip()}%"))
        if cashier_name:
            query = query.filter(User.full_name.ilike(f"%{cashier_name.strip()}%"))
        if start_at:
            query = query.filter(Sale.sale_date >= start_at)
        if end_at:
            query = query.filter(Sale.sale_date <= end_at)
        total = query.count()
        order_by = Sale.sale_date.asc() if sort == "oldest" else Sale.total_amount.desc() if sort == "total" else Sale.sale_date.desc()
        items = query.order_by(order_by).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_audits(self, sale_id: UUID, store_id: UUID) -> list[SaleAudit]:
        return self.db.query(SaleAudit).join(Sale).filter(SaleAudit.sale_id == sale_id, Sale.store_id == store_id).order_by(SaleAudit.created_at.desc()).all()

    def list_returns(self, sale_id: UUID, store_id: UUID) -> list[SaleReturn]:
        return self.db.query(SaleReturn).join(Sale).filter(SaleReturn.sale_id == sale_id, Sale.store_id == store_id).order_by(SaleReturn.created_at.desc()).all()

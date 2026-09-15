from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    purchase_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False, index=True)
    supplier_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    credit_note: Mapped[Optional[str]] = mapped_column(String(140))
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    items = relationship("PurchaseReturnItem", cascade="all, delete-orphan", back_populates="purchase_return")


class PurchaseReturnItem(Base):
    __tablename__ = "purchase_return_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    purchase_return_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_returns.id", ondelete="RESTRICT"), nullable=False, index=True)
    purchase_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    purchase_return = relationship("PurchaseReturn", back_populates="items")

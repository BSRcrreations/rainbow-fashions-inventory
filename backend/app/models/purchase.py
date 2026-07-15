from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import PurchaseStatus


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"))
    supplier_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))
    uploaded_file_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="SET NULL"))
    invoice_number: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(180))
    status: Mapped[PurchaseStatus] = mapped_column(Enum(PurchaseStatus, name="purchase_status"), nullable=False, default=PurchaseStatus.DRAFT, index=True)
    extracted_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reviewed_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    store = relationship("Store", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")
    uploaded_file = relationship("UploadedFile", back_populates="purchases")
    created_by_user = relationship("User", back_populates="created_purchases", foreign_keys=[created_by])
    confirmed_by_user = relationship("User", back_populates="confirmed_purchases", foreign_keys=[confirmed_by])
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")
    stock_movements = relationship("StockHistory", back_populates="purchase")

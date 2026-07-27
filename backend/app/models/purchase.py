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
    purchase_document_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_documents.id", ondelete="SET NULL"), unique=True)
    processing_job_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("document_processing_jobs.id", ondelete="SET NULL"))
    invoice_number: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    received_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(180))
    payment_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="CREDIT")
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(120))
    purchase_reference: Mapped[Optional[str]] = mapped_column(String(120))
    notes: Mapped[Optional[str]] = mapped_column(String(1000))
    warehouse: Mapped[Optional[str]] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[PurchaseStatus] = mapped_column(Enum(PurchaseStatus, name="purchase_status"), nullable=False, default=PurchaseStatus.DRAFT, index=True)
    extracted_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reviewed_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    packaging_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    freight_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    round_off: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    image_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    ai_processing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
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
    audits = relationship("PurchaseAudit", back_populates="purchase", cascade="all, delete-orphan")

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def balance_due(self) -> Decimal:
        return self.total_amount - self.amount_paid

    @property
    def workflow_status(self) -> str:
        if self.status == PurchaseStatus.CONFIRMED:
            return PurchaseStatus.CONFIRMED.value
        if self.status == PurchaseStatus.CANCELLED:
            return PurchaseStatus.CANCELLED.value
        return self.ai_processing_status or self.status.value

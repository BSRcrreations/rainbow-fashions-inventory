from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(140))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    gst_number: Mapped[Optional[str]] = mapped_column(String(40))
    pan_number: Mapped[Optional[str]] = mapped_column(String(40))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(120))
    state: Mapped[Optional[str]] = mapped_column(String(120))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    purchases = relationship("Purchase", back_populates="supplier")
    payments = relationship("SupplierPayment", back_populates="supplier", cascade="all, delete-orphan")


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(140))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    supplier = relationship("Supplier", back_populates="payments")

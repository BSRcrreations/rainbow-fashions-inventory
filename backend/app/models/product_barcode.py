from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"
    __table_args__ = (UniqueConstraint("store_id", "barcode", name="uq_product_barcodes_store_barcode"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    barcode_type: Mapped[str] = mapped_column(String(24), nullable=False, default="AUTO")
    manufacturer_barcode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    package_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scan_unit: Mapped[str] = mapped_column(String(24), nullable=False, default="PIECE")
    inventory_unit: Mapped[str] = mapped_column(String(24), nullable=False, default="PIECE")
    base_unit_conversion: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sale_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="PIECE_ONLY")
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    default_selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ProductBarcodeAudit(Base):
    __tablename__ = "product_barcode_audits"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    old_product_variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"))
    new_product_variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(500))
    changed_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(80))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

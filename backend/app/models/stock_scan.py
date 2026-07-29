from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import StockScanMode, StockScanQuantityMode, StockScanStatus


class StockScanSession(Base):
    __tablename__ = "stock_scan_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[StockScanMode] = mapped_column(Enum(StockScanMode, name="stock_scan_mode"), nullable=False, index=True)
    status: Mapped[StockScanStatus] = mapped_column(Enum(StockScanStatus, name="stock_scan_status"), nullable=False, default=StockScanStatus.DRAFT, index=True)
    quantity_mode: Mapped[StockScanQuantityMode] = mapped_column(Enum(StockScanQuantityMode, name="stock_scan_quantity_mode"), nullable=False, default=StockScanQuantityMode.INCREMENT)
    purchase_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchases.id", ondelete="SET NULL"), index=True)
    supplier_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    default_category_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    default_brand_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"), index=True)
    entry_date: Mapped[Optional[date]] = mapped_column(Date)
    default_purchase_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    default_selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    quick_post: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Main store")
    source_location_name: Mapped[Optional[str]] = mapped_column(String(120))
    destination_location_name: Mapped[Optional[str]] = mapped_column(String(120))
    reference: Mapped[Optional[str]] = mapped_column(String(180))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    confirmed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    items = relationship("StockScanSessionItem", back_populates="session", cascade="all, delete-orphan", order_by="StockScanSessionItem.created_at")
    purchase = relationship("Purchase")
    created_by_user = relationship("User", foreign_keys=[created_by])
    confirmed_by_user = relationship("User", foreign_keys=[confirmed_by])


class StockScanSessionItem(Base):
    __tablename__ = "stock_scan_session_items"
    __table_args__ = (UniqueConstraint("session_id", "barcode", name="uq_stock_scan_session_barcode"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_barcode_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_barcodes.id", ondelete="SET NULL"), index=True)
    barcode: Mapped[str] = mapped_column(String(80), nullable=False)
    scanned_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    package_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    difference_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    condition: Mapped[str] = mapped_column(String(40), nullable=False, default="SELLABLE")
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session = relationship("StockScanSession", back_populates="items")
    product = relationship("Product")
    product_variant = relationship("ProductVariant")

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else "Product"

    @property
    def category_name(self) -> Optional[str]:
        return self.product.category.name if self.product and self.product.category else None

    @property
    def brand_name(self) -> Optional[str]:
        return self.product.brand.name if self.product and self.product.brand else None

    @property
    def size(self) -> Optional[str]:
        return self.product_variant.size if self.product_variant else None

    @property
    def color(self) -> Optional[str]:
        return self.product_variant.color if self.product_variant else None

    @property
    def style_code(self) -> Optional[str]:
        return self.product_variant.style_code if self.product_variant else None

    @property
    def sku(self) -> Optional[str]:
        return self.product_variant.internal_sku if self.product_variant else None

    @property
    def mrp(self) -> Optional[Decimal]:
        return self.product_variant.mrp if self.product_variant else None

    @property
    def selling_price(self) -> Optional[Decimal]:
        return self.product_variant.selling_price if self.product_variant else None

    @property
    def current_physical_stock(self) -> int:
        return self.product_variant.current_stock if self.product_variant else 0

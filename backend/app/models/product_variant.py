from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("store_id", "identity_key", name="uq_product_variants_store_identity"),
        UniqueConstraint("store_id", "internal_sku", name="uq_product_variants_store_internal_sku"),
        UniqueConstraint("store_id", "barcode", name="uq_product_variants_store_barcode"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    color: Mapped[Optional[str]] = mapped_column(String(80))
    size: Mapped[Optional[str]] = mapped_column(String(60))
    style_code: Mapped[Optional[str]] = mapped_column(String(80))
    model_number: Mapped[Optional[str]] = mapped_column(String(120))
    manufacturer_sku: Mapped[Optional[str]] = mapped_column(String(120))
    internal_sku: Mapped[str] = mapped_column(String(120), nullable=False)
    barcode: Mapped[str] = mapped_column(String(80), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    last_purchase_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="variants")
    cost_lots = relationship("InventoryCostLot", back_populates="product_variant", cascade="all, delete-orphan")
    sale_items = relationship("SaleItem", back_populates="product_variant")
    purchase_items = relationship("PurchaseItem", back_populates="product_variant")
    stock_movements = relationship("StockHistory", back_populates="product_variant")


class InventoryCostLot(Base):
    __tablename__ = "inventory_cost_lots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    purchase_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchases.id", ondelete="SET NULL"), index=True)
    purchase_item_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="SET NULL"), unique=True)
    supplier_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_purchase_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    allocated_landed_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    effective_unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    lot_reference: Mapped[Optional[str]] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product_variant = relationship("ProductVariant", back_populates="cost_lots")
    stock_movements = relationship("StockHistory", back_populates="purchase_cost_lot")

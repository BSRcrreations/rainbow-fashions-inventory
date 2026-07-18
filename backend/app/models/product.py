from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import PricingType


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("category_id", "brand_id", "name", "size", "color", name="uq_products_variant"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    brand_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    size: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pricing_type: Mapped[PricingType] = mapped_column(Enum(PricingType, name="pricing_type"), nullable=False)
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    barcode: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    inventory_items = relationship("ProductInventory", back_populates="product", passive_deletes=True)
    purchase_items = relationship(
        "PurchaseItem",
        back_populates="product",
        foreign_keys="PurchaseItem.product_id",
        passive_deletes=True,
    )
    matched_purchase_items = relationship(
        "PurchaseItem",
        back_populates="matched_product",
        foreign_keys="PurchaseItem.matched_product_id",
        passive_deletes=True,
    )
    stock_movements = relationship("StockHistory", back_populates="product", passive_deletes=True)

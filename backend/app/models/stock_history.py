from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import StockMovementType


class StockHistory(Base):
    __tablename__ = "stock_history"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), index=True)
    purchase_cost_lot_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("inventory_cost_lots.id", ondelete="SET NULL"), index=True)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    store_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"))
    movement_type: Mapped[StockMovementType] = mapped_column(Enum(StockMovementType, name="stock_movement_type"), nullable=False, index=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    before_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    after_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(180))
    request_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    purchase_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchases.id", ondelete="SET NULL"))
    purchase_item_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="SET NULL"))
    sale_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sales.id", ondelete="SET NULL"), index=True)
    sale_item_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sale_items.id", ondelete="SET NULL"))
    correction_of_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_history.id", ondelete="RESTRICT"), index=True)
    correction_reason: Mapped[Optional[str]] = mapped_column(String(80))
    correction_notes: Mapped[Optional[str]] = mapped_column(String(2000))
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    movement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product = relationship("Product", back_populates="stock_movements")
    product_variant = relationship("ProductVariant", back_populates="stock_movements")
    purchase_cost_lot = relationship("InventoryCostLot", back_populates="stock_movements")
    store = relationship("Store", back_populates="stock_movements")
    purchase = relationship("Purchase", back_populates="stock_movements")
    purchase_item = relationship("PurchaseItem", back_populates="stock_movements")
    sale = relationship("Sale")
    sale_item = relationship("SaleItem")
    created_by_user = relationship("User", back_populates="stock_movements")

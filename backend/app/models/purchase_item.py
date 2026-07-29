from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    purchase_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    matched_product_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), index=True)
    category_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"))
    brand_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"))
    brand_name: Mapped[Optional[str]] = mapped_column(String(120))
    category_name: Mapped[Optional[str]] = mapped_column(String(120))
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    proposed_product_name: Mapped[Optional[str]] = mapped_column(String(180))
    barcode: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    supplier_product_code: Mapped[Optional[str]] = mapped_column(String(120))
    internal_sku: Mapped[Optional[str]] = mapped_column(String(120))
    style_code: Mapped[Optional[str]] = mapped_column(String(80))
    hsn_sac: Mapped[Optional[str]] = mapped_column(String(40))
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="Each")
    size: Mapped[str] = mapped_column(String(60), nullable=False)
    color: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    list_unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    invoiced_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    discount_type: Mapped[str] = mapped_column(String(40), nullable=False, default="NONE")
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    discount_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    discount_reason: Mapped[Optional[str]] = mapped_column(String(500))
    discount_source: Mapped[str] = mapped_column(String(40), nullable=False, default="INVOICE_EXTRACTED")
    free_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    chargeable_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    net_line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    effective_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    landed_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    allocated_invoice_discount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    promotion_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    discount_rule_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    discount_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    discount_verified_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    discount_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    match_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_FOUND")
    batch_number: Mapped[Optional[str]] = mapped_column(String(120))
    manufacturing_date: Mapped[Optional[date]] = mapped_column()
    expiry_date: Mapped[Optional[date]] = mapped_column()
    create_new_product: Mapped[bool] = mapped_column(nullable=False, default=False)
    variant_attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    classification_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    classification_verified_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    classification_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    user_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items", foreign_keys=[product_id])
    matched_product = relationship("Product", back_populates="matched_purchase_items", foreign_keys=[matched_product_id])
    product_variant = relationship("ProductVariant", back_populates="purchase_items")
    category = relationship("Category", back_populates="purchase_items")
    brand = relationship("Brand", back_populates="purchase_items")
    stock_movements = relationship("StockHistory", back_populates="purchase_item")

    @property
    def total_received_quantity(self) -> Decimal:
        return self.accepted_quantity or self.chargeable_quantity + self.free_quantity

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import SaleStatus
from app.schemas.common import ORMBaseModel


PaymentMode = Literal["CASH", "CARD", "UPI", "BANK", "OTHER"]


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)


class SaleItemUpdate(SaleItemCreate):
    pass


class SaleCreate(BaseModel):
    invoice_number: Optional[str] = Field(default=None, max_length=120)
    customer_name: Optional[str] = Field(default=None, max_length=180)
    payment_mode: PaymentMode
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    sale_date: Optional[datetime] = None
    items: list[SaleItemCreate] = Field(min_length=1)

    @field_validator("invoice_number", "customer_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SaleUpdate(BaseModel):
    customer_name: Optional[str] = Field(default=None, max_length=180)
    payment_mode: PaymentMode
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    edit_reason: str = Field(min_length=3, max_length=300)
    version: int = Field(gt=0)
    items: list[SaleItemUpdate] = Field(min_length=1)

    @field_validator("customer_name", "edit_reason", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SaleVoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    version: int = Field(gt=0)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class SaleReturnItemCreate(BaseModel):
    sale_item_id: UUID
    quantity: int = Field(gt=0)


class SaleReturnCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    refund_method: Optional[PaymentMode] = None
    items: list[SaleReturnItemCreate] = Field(min_length=1)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_return_reason(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class SaleItemRead(ORMBaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    line_total: Decimal
    sku_snapshot: Optional[str] = None
    barcode_snapshot: Optional[str] = None
    size_snapshot: Optional[str] = None
    color_snapshot: Optional[str] = None


class CashierRead(ORMBaseModel):
    id: UUID
    full_name: str


class SaleRead(ORMBaseModel):
    id: UUID
    invoice_number: str
    customer_name: Optional[str]
    payment_mode: str
    subtotal: Decimal
    discount: Decimal
    total_amount: Decimal
    cost_amount: Decimal
    profit_amount: Decimal
    status: SaleStatus
    version: int
    edit_reason: Optional[str] = None
    void_reason: Optional[str] = None
    sale_date: datetime
    cashier: Optional[CashierRead] = None
    items: list[SaleItemRead] = Field(default_factory=list)


class SaleAuditRead(ORMBaseModel):
    id: UUID
    action: str
    reason: Optional[str]
    performed_by: Optional[UUID]
    before_data: Optional[dict] = None
    after_data: Optional[dict] = None
    created_at: datetime


class SaleReturnItemRead(ORMBaseModel):
    id: UUID
    sale_item_id: UUID
    quantity: int
    refund_amount: Decimal


class SaleReturnRead(ORMBaseModel):
    id: UUID
    reason: str
    refund_method: Optional[str]
    refund_amount: Decimal
    created_at: datetime
    items: list[SaleReturnItemRead] = Field(default_factory=list)


class SaleListMeta(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int


class SaleListResponse(BaseModel):
    items: list[SaleRead]
    meta: SaleListMeta


class SalesMetric(BaseModel):
    sales: Decimal
    profit: Decimal
    orders: int


class CollectionSummary(BaseModel):
    cash: Decimal
    upi: Decimal
    card: Decimal
    other: Decimal
    total: Decimal


class SalesTrendPoint(BaseModel):
    date: date
    sales: Decimal
    profit: Decimal
    orders: int


class SalesRankingItem(BaseModel):
    id: Optional[UUID] = None
    name: str
    quantity: int
    revenue: Decimal


class InventoryAlertItem(BaseModel):
    id: UUID
    name: str
    current_stock: int
    minimum_stock: int


class SalesDashboardResponse(BaseModel):
    range_start: date
    range_end: date
    selected: SalesMetric
    today: SalesMetric
    yesterday: SalesMetric
    week: SalesMetric
    month: SalesMetric
    total_revenue: Decimal
    collection: CollectionSummary
    inventory_value: Decimal
    total_stock: int
    total_products: int
    trend: list[SalesTrendPoint]
    top_categories: list[SalesRankingItem]
    top_brands: list[SalesRankingItem]
    top_products: list[SalesRankingItem]
    recent_sales: list[SaleRead]
    low_stock: list[InventoryAlertItem]
    out_of_stock: list[InventoryAlertItem]

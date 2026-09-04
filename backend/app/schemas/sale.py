from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import SaleStatus
from app.schemas.common import ORMBaseModel


PaymentMode = Literal["CASH", "CARD", "UPI", "BANK", "CREDIT", "OTHER"]


class SaleDeleteCheckRequest(BaseModel):
    sale_ids: list[UUID] = Field(min_length=1, max_length=100)


class SaleDeleteRequest(SaleDeleteCheckRequest):
    delete_password: str = Field(min_length=1, max_length=256)


class SaleItemCreate(BaseModel):
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    quantity: int = Field(gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_sellable_item(self) -> "SaleItemCreate":
        if not self.product_id and not self.product_variant_id:
            raise ValueError("product_variant_id is required")
        return self


class SaleItemUpdate(SaleItemCreate):
    pass


class SaleCreate(BaseModel):
    invoice_number: Optional[str] = Field(default=None, max_length=120)
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = Field(default=None, max_length=180)
    customer_phone: Optional[str] = Field(default=None, max_length=30)
    customer_details: Optional[str] = Field(default=None, max_length=2000)
    payment_mode: PaymentMode
    discount_type: str = "PERCENTAGE"
    discount_value: Decimal = Field(default=Decimal("0"))
    sale_date: Optional[datetime] = None
    items: list[SaleItemCreate] = Field(min_length=1)

    @field_validator("invoice_number", "customer_name", "customer_phone", "customer_details", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @model_validator(mode="after")
    def keep_sale_items_on_one_inventory_contract(self) -> "SaleCreate":
        has_variant_items = [item.product_variant_id is not None for item in self.items]
        if any(has_variant_items) and not all(has_variant_items):
            raise ValueError("Use product_variant_id for every item when creating a variant-level sale")
        return self


class SaleUpdate(BaseModel):
    customer_id: Optional[UUID] = None
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
    product_variant_id: Optional[UUID] = None
    product_name: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    line_total: Decimal
    sku_snapshot: Optional[str] = None
    barcode_snapshot: Optional[str] = None
    size_snapshot: Optional[str] = None
    color_snapshot: Optional[str] = None
    style_snapshot: Optional[str] = None
    mrp_snapshot: Optional[Decimal] = None


class SaleCatalogVariant(BaseModel):
    variant_id: UUID
    product_id: UUID
    size: Optional[str] = None
    color: Optional[str] = None
    style_code: Optional[str] = None
    sku: str
    barcode: str
    mrp: Optional[Decimal] = None
    selling_price: Decimal
    available_stock: int
    classification_review_required: bool = False
    is_active: bool
    scan_unit: str = "PIECE"
    pieces_per_pack: int = 1


class SaleCatalogProduct(BaseModel):
    product_id: UUID
    name: str
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    product_image_url: Optional[str] = None
    variant_count: int = 0
    total_stock: int = 0
    minimum_stock: int = 0
    total_available_stock: int
    variants: list[SaleCatalogVariant] = Field(default_factory=list)


class CashierRead(ORMBaseModel):
    id: UUID
    full_name: str


class SaleRead(ORMBaseModel):
    id: UUID
    invoice_number: str
    customer_id: Optional[UUID] = None
    customer_name: Optional[str]
    payment_mode: str
    subtotal: Decimal
    discount: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    grand_total: Decimal
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

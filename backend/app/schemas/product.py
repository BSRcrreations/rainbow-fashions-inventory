from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import PricingType
from app.schemas.brand import BrandRead
from app.schemas.category import CategoryRead
from app.schemas.common import ORMBaseModel
from app.schemas.subcategory import SubCategoryRead


class ProductBase(BaseModel):
    category_id: UUID
    subcategory_id: UUID
    brand_id: UUID
    sku: Optional[str] = Field(default=None, max_length=80)
    name: str = Field(min_length=2, max_length=180)
    size: str = Field(min_length=1, max_length=60)
    color: str = Field(min_length=1, max_length=80)
    purchase_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    pricing_type: PricingType
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)
    barcode: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("sku", "barcode", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("name", "size", "color", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @model_validator(mode="after")
    def validate_pricing(self) -> "ProductBase":
        if self.pricing_type == PricingType.MRP and self.mrp is None:
            raise ValueError("MRP is required when pricing_type is MRP")
        return self


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    sku: Optional[str] = Field(default=None, max_length=80)
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    size: Optional[str] = Field(default=None, min_length=1, max_length=60)
    color: Optional[str] = Field(default=None, min_length=1, max_length=80)
    purchase_price: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    pricing_type: Optional[PricingType] = None
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    current_stock: Optional[int] = Field(default=None, ge=0)
    minimum_stock: Optional[int] = Field(default=None, ge=0)
    barcode: Optional[str] = Field(default=None, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("sku", "barcode", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("name", "size", "color", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        return value.strip()


class ProductRead(ProductBase, ORMBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead] = None
    subcategory: Optional[SubCategoryRead] = None
    brand: Optional[BrandRead] = None


class ProductListMeta(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    meta: ProductListMeta


class ProductBulkIds(BaseModel):
    product_ids: list[UUID] = Field(min_length=1)


class ProductBulkCategoryUpdate(ProductBulkIds):
    category_id: UUID


class ProductBulkBrandUpdate(ProductBulkIds):
    brand_id: UUID


class ProductBulkStockUpdate(ProductBulkIds):
    direction: Literal["INCREASE", "DECREASE"]
    qty: int = Field(gt=0)
    reference: str = Field(min_length=2, max_length=180)


class ProductImportSummary(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[dict[str, str]]


class ProductCodeResponse(BaseModel):
    value: str


class ProductListFilters(BaseModel):
    search: Optional[str] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    stock_status: Optional[Literal["low", "out", "in"]] = None
    min_price: Optional[Decimal] = Field(default=None, ge=0)
    max_price: Optional[Decimal] = Field(default=None, ge=0)
    created_from: Optional[date] = None
    created_to: Optional[date] = None
    sort_by: Literal["name", "sku", "selling_price", "purchase_price", "stock", "created_at", "updated_at"] = "name"
    sort_dir: Literal["asc", "desc"] = "asc"

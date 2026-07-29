from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    size: Optional[str] = Field(default=None, min_length=1, max_length=60)
    color: Optional[str] = Field(default=None, min_length=1, max_length=80)
    purchase_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    pricing_type: PricingType
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)
    barcode: Optional[str] = Field(default=None, max_length=80)
    product_date: date
    description: Optional[str] = Field(default=None, max_length=2000)
    hsn_sac: Optional[str] = Field(default=None, max_length=40)
    unit: str = Field(default="Each", min_length=1, max_length=40)
    warehouse: Optional[str] = Field(default=None, max_length=120)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    is_test_data: bool = False

    @field_validator("sku", "barcode", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("size", "color", mode="before")
    @classmethod
    def normalize_optional_variant_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_pricing(self) -> "ProductBase":
        if self.pricing_type == PricingType.MRP and self.mrp is None:
            raise ValueError("MRP is required when pricing_type is MRP")
        return self


class ProductCreate(ProductBase):
    colors: list[str] = Field(default_factory=list, max_length=50)
    sizes: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("colors", "sizes", mode="before")
    @classmethod
    def normalize_variant_values(cls, values: object) -> object:
        if not isinstance(values, list):
            return values
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result


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
    product_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    hsn_sac: Optional[str] = Field(default=None, max_length=40)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=40)
    warehouse: Optional[str] = Field(default=None, max_length=120)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    is_test_data: Optional[bool] = None
    colors: Optional[list[str]] = Field(default=None, max_length=50)
    sizes: Optional[list[str]] = Field(default=None, max_length=50)

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
        stripped = value.strip()
        return stripped or None

    @field_validator("colors", "sizes", mode="before")
    @classmethod
    def normalize_variant_values(cls, values: object) -> object:
        if values is None or not isinstance(values, list):
            return values
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result


class ProductVariantRead(ORMBaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    product_id: UUID
    store_id: UUID
    color: Optional[str] = None
    size: Optional[str] = None
    style_code: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer_sku: Optional[str] = None
    internal_sku: str
    barcode: str
    mrp: Optional[Decimal] = None
    selling_price: Decimal
    last_purchase_cost: Decimal
    average_cost: Decimal
    current_stock: int
    classification_review_required: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductRead(ProductBase, ORMBaseModel):
    id: UUID
    store_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead] = None
    subcategory: Optional[SubCategoryRead] = None
    brand: Optional[BrandRead] = None
    variants: list[ProductVariantRead] = Field(default_factory=list)


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


class ProductBulkDeleteRequest(ProductBulkIds):
    confirmation: str = Field(min_length=1, max_length=40)


class ProductBulkPurgeTestDataRequest(ProductBulkIds):
    confirmation: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=3, max_length=500)


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

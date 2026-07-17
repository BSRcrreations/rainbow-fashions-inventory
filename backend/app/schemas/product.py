from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import PricingType
from app.schemas.brand import BrandRead
from app.schemas.category import CategoryRead
from app.schemas.common import ORMBaseModel


class ProductBase(BaseModel):
    category_id: UUID
    brand_id: UUID
    name: str = Field(min_length=2, max_length=180)
    size: str = Field(min_length=1, max_length=60)
    color: str = Field(min_length=1, max_length=80)
    purchase_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    pricing_type: PricingType
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    gst_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    hsn_code: Optional[str] = Field(default=None, max_length=20)
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)
    barcode: Optional[str] = Field(default=None, max_length=80)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_pricing(self) -> "ProductBase":
        if self.pricing_type == PricingType.MRP and self.mrp is None:
            raise ValueError("MRP is required when pricing_type is MRP")
        return self


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    size: Optional[str] = Field(default=None, min_length=1, max_length=60)
    color: Optional[str] = Field(default=None, min_length=1, max_length=80)
    purchase_price: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    pricing_type: Optional[PricingType] = None
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    gst_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    hsn_code: Optional[str] = Field(default=None, max_length=20)
    current_stock: Optional[int] = Field(default=None, ge=0)
    minimum_stock: Optional[int] = Field(default=None, ge=0)
    barcode: Optional[str] = Field(default=None, max_length=80)
    is_active: Optional[bool] = None


class ProductRead(ProductBase, ORMBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead] = None
    brand: Optional[BrandRead] = None

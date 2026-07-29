from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import StockScanMode, StockScanQuantityMode, StockScanStatus
from app.schemas.common import ORMBaseModel


class StockScanSessionCreate(BaseModel):
    mode: StockScanMode = StockScanMode.PHYSICAL_COUNT
    quantity_mode: StockScanQuantityMode = StockScanQuantityMode.INCREMENT
    purchase_id: Optional[UUID] = None
    location_name: str = Field(default="Main store", min_length=2, max_length=120)
    source_location_name: Optional[str] = Field(default=None, max_length=120)
    destination_location_name: Optional[str] = Field(default=None, max_length=120)
    reference: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("location_name", "source_location_name", "destination_location_name", "reference", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class StockScanSessionUpdate(BaseModel):
    quantity_mode: Optional[StockScanQuantityMode] = None
    purchase_id: Optional[UUID] = None
    location_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    source_location_name: Optional[str] = Field(default=None, max_length=120)
    destination_location_name: Optional[str] = Field(default=None, max_length=120)
    reference: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=2000)


class StockScanRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=100000)

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str) -> str:
        barcode = value.strip()
        if not barcode:
            raise ValueError("Barcode is required")
        return barcode


class StockScanItemUpdate(BaseModel):
    scanned_quantity: int = Field(ge=0, le=100000)
    condition: Optional[str] = Field(default=None, min_length=2, max_length=40)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class BarcodeAssignment(BaseModel):
    barcode: str = Field(min_length=1, max_length=80)

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str) -> str:
        barcode = value.strip()
        if not barcode:
            raise ValueError("Barcode is required")
        return barcode


class BarcodeOnboarding(BaseModel):
    product_variant_id: UUID
    barcode: str = Field(min_length=1, max_length=80)
    barcode_type: str = Field(default="AUTO", max_length=24)
    manufacturer_barcode: bool = True
    package_quantity: int = Field(default=1, ge=1, le=100000)
    scan_unit: str = Field(default="PIECE", max_length=24)
    inventory_unit: str = Field(default="PIECE", max_length=24)
    default_selling_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    verified: bool = True

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str) -> str:
        barcode = value.strip()
        if not barcode:
            raise ValueError("Barcode is required")
        return barcode

    @model_validator(mode="after")
    def validate_package_configuration(self) -> "BarcodeOnboarding":
        self.scan_unit = self.scan_unit.strip().upper()
        self.inventory_unit = self.inventory_unit.strip().upper()
        if self.package_quantity > 1 and self.scan_unit != "PACK":
            raise ValueError("Package quantities above one must use PACK as the scan unit")
        return self


class StockScanConfirmRequest(BaseModel):
    reference: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ProductVariantBarcodeRead(ORMBaseModel):
    product_id: UUID
    variant_id: UUID
    product_name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    style_code: Optional[str] = None
    sku: str
    barcode: str
    mrp: Optional[Decimal] = None
    selling_price: Decimal
    current_physical_stock: int
    current_available_stock: int
    active: bool
    package_quantity: int = 1
    scan_unit: str = "PIECE"
    inventory_unit: str = "PIECE"
    base_unit_conversion: int = 1


class StockScanSessionItemRead(ORMBaseModel):
    id: UUID
    product_id: UUID
    product_variant_id: UUID
    product_barcode_id: Optional[UUID] = None
    barcode: str
    product_name: str
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    style_code: Optional[str] = None
    sku: Optional[str] = None
    mrp: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    current_physical_stock: int
    scanned_quantity: int
    package_quantity: int = 1
    base_quantity: int = 0
    expected_quantity: Optional[int] = None
    difference_quantity: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    condition: str
    last_scanned_at: datetime
    created_at: datetime


class StockScanSessionRead(ORMBaseModel):
    id: UUID
    store_id: UUID
    mode: StockScanMode
    status: StockScanStatus
    quantity_mode: StockScanQuantityMode
    purchase_id: Optional[UUID] = None
    location_name: str
    source_location_name: Optional[str] = None
    destination_location_name: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    created_by: UUID
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: list[StockScanSessionItemRead]


class StockScanValidationRead(BaseModel):
    valid: bool
    messages: list[str]
    session: StockScanSessionRead

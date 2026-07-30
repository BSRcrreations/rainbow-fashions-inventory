from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.models.enums import PricingType, StockScanMode, StockScanQuantityMode, StockScanStatus
from app.schemas.common import ORMBaseModel


class StockScanSessionCreate(BaseModel):
    mode: StockScanMode = StockScanMode.PHYSICAL_COUNT
    quantity_mode: StockScanQuantityMode = StockScanQuantityMode.INCREMENT
    purchase_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    default_category_id: Optional[UUID] = None
    default_brand_id: Optional[UUID] = None
    entry_date: Optional[date] = None
    default_purchase_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    default_selling_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quick_post: bool = False
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
    supplier_id: Optional[UUID] = None
    default_category_id: Optional[UUID] = None
    default_brand_id: Optional[UUID] = None
    entry_date: Optional[date] = None
    default_purchase_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    default_selling_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quick_post: Optional[bool] = None
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
    sale_mode: str = Field(default="PIECE_ONLY", max_length=24)
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
        self.sale_mode = self.sale_mode.strip().upper()
        if self.package_quantity > 1 and self.scan_unit != "PACK":
            raise ValueError("Package quantities above one must use PACK as the scan unit")
        return self


class BarcodeProductOnboarding(BaseModel):
    """Creates or selects the exact sellable variant, then adds it to one draft session."""

    model_config = ConfigDict(protected_namespaces=())

    session_id: UUID
    action: Literal["EXISTING_VARIANT", "NEW_VARIANT", "NEW_PRODUCT"]
    barcode: str = Field(min_length=1, max_length=80)
    product_variant_id: Optional[UUID] = None
    existing_product_id: Optional[UUID] = None
    product_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    product_code: Optional[str] = Field(default=None, max_length=80)
    style_code: Optional[str] = Field(default=None, max_length=80)
    model_number: Optional[str] = Field(default=None, max_length=120)
    manufacturer_sku: Optional[str] = Field(default=None, max_length=120)
    internal_sku: Optional[str] = Field(default=None, max_length=120)
    size: Optional[str] = Field(default=None, max_length=60)
    color: Optional[str] = Field(default=None, max_length=80)
    hsn_sac: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=500)
    product_date: Optional[date] = None
    pricing_type: PricingType = PricingType.OWN_PRICE
    minimum_stock: int = Field(default=0, ge=0, le=100000)
    alternate_barcode: Optional[str] = Field(default=None, max_length=80)
    package_barcode: Optional[str] = Field(default=None, max_length=80)
    package_barcode_quantity: int = Field(default=1, ge=1, le=100000)
    quantity: int = Field(default=1, ge=1, le=100000)
    package_quantity: int = Field(default=1, ge=1, le=100000)
    scan_unit: Literal["PIECE", "PACK"] = "PIECE"
    inventory_unit: str = Field(default="PIECE", min_length=1, max_length=24)
    sale_mode: Literal["PACK_ONLY", "PIECE_ONLY", "BOTH"] = "PIECE_ONLY"
    purchase_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    mrp: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    condition: str = Field(default="SELLABLE", min_length=2, max_length=40)

    @field_validator("barcode", "alternate_barcode", "package_barcode")
    @classmethod
    def normalize_onboard_barcode(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value and info.field_name == "barcode":
            raise ValueError("Barcode is required")
        return value or None

    @field_validator("product_name", "product_code", "style_code", "model_number", "manufacturer_sku", "internal_sku", "size", "color", "hsn_sac", "description", "image_url", "inventory_unit", "condition", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_onboarding(self) -> "BarcodeProductOnboarding":
        if self.package_quantity > 1 and self.scan_unit != "PACK":
            raise ValueError("Package quantities above one must use PACK as the scan unit")
        if self.pricing_type == PricingType.MRP and self.mrp is None:
            raise ValueError("MRP is required when pricing type is MRP")
        if self.mrp is not None and self.selling_price > self.mrp:
            raise ValueError("Selling price cannot be greater than MRP")
        optional_barcodes = [value for value in (self.alternate_barcode, self.package_barcode) if value]
        if len(set([self.barcode, *optional_barcodes])) != len([self.barcode, *optional_barcodes]):
            raise ValueError("Each barcode must be unique")
        if self.action == "EXISTING_VARIANT" and not self.product_variant_id:
            raise ValueError("Select the existing variant to assign this barcode")
        if self.action == "NEW_VARIANT" and not self.existing_product_id:
            raise ValueError("Select the product for the new variant")
        if self.action == "NEW_PRODUCT":
            if not self.product_name:
                raise ValueError("Enter a product name")
            if not self.category_id:
                raise ValueError("Select a category")
            if not self.brand_id:
                raise ValueError("Select a brand or choose Unbranded")
        return self


class LabelExtractionSuggestion(BaseModel):
    value: str
    confidence: float = Field(ge=0, le=1)
    source_text: str
    bounding_box: Optional[dict[str, float]] = None
    requires_review: bool = True


class BarcodeImageResolutionRead(BaseModel):
    image_url: str
    suggestions: dict[str, LabelExtractionSuggestion]


class StockScanConfirmRequest(BaseModel):
    reference: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ProductVariantBarcodeRead(ORMBaseModel):
    product_id: UUID
    variant_id: UUID
    product_name: str
    category: Optional[str] = None
    category_id: Optional[UUID] = None
    brand: Optional[str] = None
    brand_id: Optional[UUID] = None
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
    sale_mode: str = "PIECE_ONLY"


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
    supplier_id: Optional[UUID] = None
    default_category_id: Optional[UUID] = None
    default_brand_id: Optional[UUID] = None
    entry_date: Optional[date] = None
    default_purchase_cost: Optional[Decimal] = None
    default_selling_price: Optional[Decimal] = None
    quick_post: bool = False
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

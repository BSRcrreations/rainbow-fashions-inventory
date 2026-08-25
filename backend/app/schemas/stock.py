from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import StockMovementType
from app.schemas.common import ORMBaseModel


class InventoryValuationRead(BaseModel):
    inventory_value: Decimal


class StockAdjustmentCreate(BaseModel):
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    qty: int = Field(gt=0)
    direction: str = Field(pattern="^(INCREASE|DECREASE)$")
    adjustment_type: Literal["ADD_STOCK", "REMOVE_STOCK", "SET_COUNTED_QUANTITY"] = "ADD_STOCK"
    reason: Literal["CUSTOMER_RETURN", "SUPPLIER_RETURN", "DAMAGE", "MANUAL_ADJUSTMENT"] = "MANUAL_ADJUSTMENT"
    reference: str = Field(min_length=2, max_length=180)

    @model_validator(mode="after")
    def require_stock_target(self) -> "StockAdjustmentCreate":
        if not self.product_id and not self.product_variant_id:
            raise ValueError("Product variant is required")
        return self


class StockCorrectionCreate(BaseModel):
    """Correct an existing movement without editing or deleting its audit trail."""

    correct_quantity: int = Field(ge=0, le=100000)
    reason: Literal[
        "DATA_ENTRY_MISTAKE",
        "DAMAGED_STOCK",
        "MISSING_STOCK",
        "DUPLICATE_OPENING_STOCK",
        "INCORRECT_BARCODE_ASSIGNMENT",
        "INCORRECT_VARIANT_SELECTED",
        "TEST_DATA",
        "OTHER",
    ]
    reference: Optional[str] = Field(default=None, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_notes_for_other(self) -> "StockCorrectionCreate":
        if self.reason == "OTHER" and not (self.notes or "").strip():
            raise ValueError("Notes are required when correction reason is Other")
        return self


class VariantCorrectionMoveRequest(BaseModel):
    """Move already-confirmed stock to the correct variant without rewriting history."""

    source_variant_id: UUID
    destination_variant_id: UUID
    quantity: int = Field(gt=0, le=100000)
    reason: Literal[
        "WRONG_SIZE_ENTERED",
        "INCORRECT_VARIANT_SELECTED",
        "INCORRECT_BARCODE_ASSIGNMENT",
        "DATA_ENTRY_MISTAKE",
        "TEST_DATA",
        "OTHER",
    ]
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_move(self) -> "VariantCorrectionMoveRequest":
        if self.source_variant_id == self.destination_variant_id:
            raise ValueError("Choose two different variants for a correction")
        if self.reason == "OTHER" and not (self.notes or "").strip():
            raise ValueError("Notes are required when correction reason is Other")
        return self


class VariantCorrectionVariantRead(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_name: str
    size: Optional[str] = None
    color: Optional[str] = None
    sku: str
    barcode: str
    before_stock: int
    after_stock: int


class VariantCorrectionPreviewResponse(BaseModel):
    source: VariantCorrectionVariantRead
    destination: VariantCorrectionVariantRead
    quantity: int
    reason: str
    notes: Optional[str] = None
    reference: str
    request_id: str


class VariantCorrectionMoveResponse(VariantCorrectionPreviewResponse):
    source_history_id: UUID
    destination_history_id: UUID
    already_completed: bool = False


class StockProductRead(ORMBaseModel):
    id: UUID
    name: str
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str]


class StockUserRead(ORMBaseModel):
    id: UUID
    full_name: str


class StockSaleCreate(BaseModel):
    product_id: UUID
    qty: int = Field(gt=0)
    reference: Optional[str] = Field(default=None, max_length=180)


class StockHistoryRead(ORMBaseModel):
    id: UUID
    product_id: UUID
    product_variant_id: Optional[UUID] = None
    store_id: Optional[UUID]
    movement_type: StockMovementType
    qty: int
    before_stock: int
    after_stock: int
    reference: Optional[str]
    purchase_id: Optional[UUID]
    purchase_item_id: Optional[UUID]
    sale_id: Optional[UUID]
    sale_item_id: Optional[UUID]
    created_by: Optional[UUID]
    product: Optional[StockProductRead] = None
    created_by_user: Optional[StockUserRead] = None
    movement_date: datetime
    created_at: datetime
    correction_of_id: Optional[UUID] = None
    correction_reason: Optional[str] = None
    correction_notes: Optional[str] = None
    request_id: Optional[str] = None


class StockResetPreviewRequest(BaseModel):
    scope: Literal[
        "SELECTED_VARIANTS",
        "PRODUCT",
        "CATEGORY",
        "BRAND",
        "ALL_CURRENT_STOCK",
        "ALL_OPENING_STOCK",
    ] = "SELECTED_VARIANTS"
    variant_ids: list[UUID] = Field(default_factory=list)
    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_scope_target(self) -> "StockResetPreviewRequest":
        if self.scope == "SELECTED_VARIANTS" and not self.variant_ids:
            raise ValueError("Select at least one variant to preview")
        if self.scope == "PRODUCT" and not self.product_id:
            raise ValueError("Product is required for product reset scope")
        if self.scope == "CATEGORY" and not self.category_id:
            raise ValueError("Category is required for category reset scope")
        if self.scope == "BRAND" and not self.brand_id:
            raise ValueError("Brand is required for brand reset scope")
        return self


class StockResetConfirmRequest(StockResetPreviewRequest):
    confirmation: str = Field(min_length=1, max_length=180)
    owner_password: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_confirmation_text(self) -> "StockResetConfirmRequest":
        expected = "This will set the selected existing stock quantities to zero. Products, variants and barcodes will remain available."
        if self.confirmation.strip() != expected:
            raise ValueError("Confirmation text does not match")
        return self


class StockResetPreviewItem(BaseModel):
    variant_id: UUID
    product_id: UUID
    product: str
    brand: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    barcode: str
    sku: str
    current_stock: int
    reset_quantity: int
    resulting_stock: int
    unit_cost: Decimal
    inventory_value: Decimal


class StockResetPreviewResponse(BaseModel):
    variants: list[StockResetPreviewItem]
    total_products: int
    total_variants: int
    total_pieces: int
    total_inventory_value: Decimal
    request_id: str
    classification_warning: Optional[str] = None


class StockResetResponse(StockResetPreviewResponse):
    stock_history_ids: list[UUID]
    already_completed: bool = False

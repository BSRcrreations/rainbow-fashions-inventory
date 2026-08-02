from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import StockMovementType
from app.schemas.common import ORMBaseModel


class StockAdjustmentCreate(BaseModel):
    product_id: UUID
    qty: int = Field(gt=0)
    direction: str = Field(pattern="^(INCREASE|DECREASE)$")
    reason: Literal["CUSTOMER_RETURN", "SUPPLIER_RETURN", "DAMAGE", "MANUAL_ADJUSTMENT"] = "MANUAL_ADJUSTMENT"
    reference: str = Field(min_length=2, max_length=180)


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

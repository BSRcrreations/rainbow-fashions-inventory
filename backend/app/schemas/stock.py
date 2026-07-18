from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import StockMovementType
from app.schemas.common import ORMBaseModel


class StockAdjustmentCreate(BaseModel):
    product_id: UUID
    qty: int = Field(gt=0)
    direction: str = Field(pattern="^(INCREASE|DECREASE)$")
    reason: Literal["CUSTOMER_RETURN", "SUPPLIER_RETURN", "DAMAGE", "MANUAL_ADJUSTMENT"] = "MANUAL_ADJUSTMENT"
    reference: str = Field(min_length=2, max_length=180)


class StockProductRead(ORMBaseModel):
    id: UUID
    name: str
    size: str
    color: str
    sku: Optional[str]


class StockUserRead(ORMBaseModel):
    id: UUID
    full_name: str


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

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import StockMovementType
from app.schemas.common import ORMBaseModel


class StockAdjustmentCreate(BaseModel):
    product_id: UUID
    qty: int = Field(gt=0)
    direction: str = Field(pattern="^(INCREASE|DECREASE)$")
    reference: Optional[str] = Field(default=None, max_length=180)


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
    movement_date: datetime
    created_at: datetime

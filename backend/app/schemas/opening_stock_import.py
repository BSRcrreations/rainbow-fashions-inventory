from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import OpeningStockImportStatus


OPENING_STOCK_CONFIRMATION = "POST OPENING STOCK"


class OpeningStockImportErrorRead(BaseModel):
    row_number: Optional[int] = None
    field: Optional[str] = None
    code: str
    message: str


class OpeningStockImportRowRead(BaseModel):
    row_number: int
    validation_status: str
    normalized_data: dict = Field(default_factory=dict)
    errors: list[OpeningStockImportErrorRead] = Field(default_factory=list)


class OpeningStockImportRead(BaseModel):
    id: UUID
    status: OpeningStockImportStatus
    original_filename: str
    file_size_bytes: int
    row_count: int
    valid_row_count: int
    error_count: int
    total_quantity: int
    total_cost_value: Decimal
    total_retail_value: Decimal
    validation_summary: dict = Field(default_factory=dict)
    backup_evidence: dict = Field(default_factory=dict)
    posted_at: Optional[datetime] = None
    reversed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OpeningStockImportDetail(OpeningStockImportRead):
    rows: list[OpeningStockImportRowRead] = Field(default_factory=list)
    errors: list[OpeningStockImportErrorRead] = Field(default_factory=list)


class OpeningStockImportConfirm(BaseModel):
    confirmation: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=120)


class OpeningStockImportReverse(BaseModel):
    confirmation: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=8, max_length=500)


class OpeningStockImportReport(BaseModel):
    import_id: UUID
    status: OpeningStockImportStatus
    created_products: int
    created_variants: int
    created_barcodes: int
    created_cost_lots: int
    created_movements: int
    total_quantity: int
    total_cost_value: Decimal
    total_retail_value: Decimal
    already_completed: bool = False

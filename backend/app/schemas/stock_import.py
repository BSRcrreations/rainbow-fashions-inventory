from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


StockImportStatus = Literal[
    "UPLOADED", "VALIDATING", "VALIDATION_FAILED", "READY", "BACKUP_STARTED",
    "BACKUP_FAILED", "COMMITTING", "COMPLETED", "FAILED", "ROLLBACK_PENDING",
    "ROLLED_BACK", "ROLLBACK_FAILED",
]


class StockImportRowRead(ORMBaseModel):
    id: UUID
    row_number: int
    sku: Optional[str] = None
    barcode: Optional[str] = None
    quantity: Optional[int] = None
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    validation_errors: list = Field(default_factory=list)
    normalized_data: dict = Field(default_factory=dict)


class StockImportRead(ORMBaseModel):
    id: UUID
    store_id: UUID
    import_type: str
    status: StockImportStatus
    source_filename: str
    file_sha256: str
    summary: dict = Field(default_factory=dict)
    failure_details: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StockImportPreview(StockImportRead):
    rows: list[StockImportRowRead] = Field(default_factory=list)


class StockImportRollbackRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class StockImportRollbackResponse(BaseModel):
    import_id: UUID
    status: StockImportStatus
    already_rolled_back: bool = False

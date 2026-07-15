from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PurchaseStatus
from app.schemas.common import ORMBaseModel


class ExtractedInvoiceItem(BaseModel):
    brand: Optional[str] = None
    category: Optional[str] = None
    product_name: str = Field(min_length=1)
    size: str = Field(min_length=1)
    color: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    purchase_price: Decimal = Field(ge=0)
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    total_amount: Decimal = Field(ge=0)
    matched_product_id: Optional[UUID] = None
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)


class ExtractedInvoice(BaseModel):
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[date] = None
    total_amount: Decimal = Field(default=0, ge=0)
    items: list[ExtractedInvoiceItem] = Field(default_factory=list)


class PurchaseItemReview(BaseModel):
    product_id: Optional[UUID] = None
    matched_product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    product_name: str = Field(min_length=1, max_length=180)
    size: str = Field(min_length=1, max_length=60)
    color: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0)
    purchase_price: Decimal = Field(ge=0)
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    line_total: Decimal = Field(ge=0)
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)


class PurchaseReviewUpdate(BaseModel):
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    items: list[PurchaseItemReview] = Field(min_length=1)


class PurchaseItemRead(PurchaseItemReview, ORMBaseModel):
    id: UUID


class PurchaseRead(ORMBaseModel):
    id: UUID
    store_id: Optional[UUID]
    supplier_id: Optional[UUID]
    uploaded_file_id: Optional[UUID]
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    supplier_name: Optional[str]
    status: PurchaseStatus
    extracted_payload: dict
    reviewed_payload: dict
    total_amount: Decimal
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseItemRead] = Field(default_factory=list)


class PurchaseUploadResponse(BaseModel):
    purchase: PurchaseRead
    extracted_invoice: ExtractedInvoice
    review_items: list[PurchaseItemReview]

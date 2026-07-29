from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PurchaseStatus
from app.models.enums import DocumentJobStatus
from app.schemas.common import ORMBaseModel


PurchaseItemDiscountType = Literal["NONE", "PERCENTAGE", "FIXED_PER_UNIT", "FIXED_PER_LINE", "FINAL_UNIT_PRICE", "QUANTITY_SLAB", "FREE_QUANTITY", "MANUAL"]
InvoiceDiscountType = Literal["NONE", "PERCENTAGE", "FIXED_AMOUNT", "TRADE_DISCOUNT", "CASH_DISCOUNT", "COUPON", "PROMOTIONAL", "MANUAL_ADJUSTMENT"]
InvoiceDiscountAllocationMethod = Literal["BY_ITEM_VALUE", "BY_TAXABLE_VALUE", "BY_QUANTITY", "EQUALLY", "MANUAL", "DO_NOT_ALLOCATE"]
DiscountSource = Literal["INVOICE_EXTRACTED", "USER_ENTERED", "SUPPLIER_AGREEMENT", "QUANTITY_SLAB", "PROMOTION", "COUPON", "CASH_DISCOUNT", "SYSTEM_CALCULATED", "DERIVED_FROM_PRICES", "MANUAL_OVERRIDE"]


class PurchaseDeleteCheckRequest(BaseModel):
    purchase_ids: list[UUID] = Field(min_length=1, max_length=100)


class PurchaseDeleteRequest(PurchaseDeleteCheckRequest):
    delete_password: str = Field(min_length=1, max_length=256)


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
    barcode: Optional[str] = None
    unit: str = "Each"
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)


class ExtractedInvoice(BaseModel):
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    # Keep the public `date` field while avoiding a postponed-annotation name collision.
    date: Optional[date_type] = None
    total_amount: Decimal = Field(default=0, ge=0)
    items: list[ExtractedInvoiceItem] = Field(default_factory=list)


class PurchaseItemReview(BaseModel):
    product_id: Optional[UUID] = None
    matched_product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    product_name: str = Field(min_length=1, max_length=180)
    proposed_product_name: Optional[str] = Field(default=None, min_length=1, max_length=180)
    barcode: Optional[str] = Field(default=None, max_length=80)
    supplier_product_code: Optional[str] = Field(default=None, max_length=120)
    internal_sku: Optional[str] = Field(default=None, max_length=120)
    style_code: Optional[str] = Field(default=None, max_length=80)
    hsn_sac: Optional[str] = Field(default=None, max_length=40)
    unit: str = Field(default="Each", min_length=1, max_length=40)
    size: str = Field(default="", max_length=60)
    color: str = Field(default="", max_length=80)
    quantity: int = Field(gt=0)
    purchase_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    list_unit_price: Optional[Decimal] = Field(default=None, ge=0)
    invoiced_unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_type: PurchaseItemDiscountType = "NONE"
    discount_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    discount_per_unit: Decimal = Field(default=Decimal("0"), ge=0)
    discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    discount_reason: Optional[str] = Field(default=None, max_length=500)
    discount_source: DiscountSource = "INVOICE_EXTRACTED"
    free_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    chargeable_quantity: Optional[Decimal] = Field(default=None, ge=0)
    accepted_quantity: Optional[Decimal] = Field(default=None, ge=0)
    gross_amount: Optional[Decimal] = Field(default=None, ge=0)
    taxable_amount: Optional[Decimal] = Field(default=None, ge=0)
    net_line_amount: Optional[Decimal] = Field(default=None, ge=0)
    effective_unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    landed_unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    allocated_invoice_discount: Decimal = Field(default=Decimal("0"), ge=0)
    promotion_id: Optional[UUID] = None
    discount_rule_id: Optional[UUID] = None
    discount_verified: bool = False
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    line_total: Decimal = Field(ge=0)
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)
    match_status: str = "NOT_FOUND"
    batch_number: Optional[str] = Field(default=None, max_length=120)
    manufacturing_date: Optional[date_type] = None
    expiry_date: Optional[date_type] = None
    create_new_product: bool = False
    variant_attributes: dict[str, str] = Field(default_factory=dict)
    classification_verified: bool = False
    user_verified: bool = False


class PurchaseReviewUpdate(BaseModel):
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    purchase_date: date_type
    invoice_date: Optional[date_type] = None
    received_date: Optional[date_type] = None
    duplicate_acknowledged: bool = False
    items: list[PurchaseItemReview] = Field(min_length=1)


class PurchasePatch(BaseModel):
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = Field(default=None, max_length=180)
    invoice_number: Optional[str] = Field(default=None, min_length=1, max_length=120)
    purchase_date: Optional[date_type] = None
    invoice_date: Optional[date_type] = None
    received_date: Optional[date_type] = None
    due_date: Optional[date_type] = None
    payment_mode: Optional[str] = Field(default=None, max_length=40)
    amount_paid: Optional[Decimal] = Field(default=None, ge=0)
    place_of_supply: Optional[str] = Field(default=None, max_length=120)
    purchase_reference: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=1000)
    warehouse: Optional[str] = Field(default=None, max_length=120)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    packaging_amount: Optional[Decimal] = Field(default=None, ge=0)
    freight_amount: Optional[Decimal] = Field(default=None, ge=0)
    round_off: Optional[Decimal] = None
    invoice_discount_type: Optional[InvoiceDiscountType] = None
    invoice_discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=100)
    invoice_discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    invoice_discount_reason: Optional[str] = Field(default=None, max_length=500)
    invoice_discount_allocation_method: Optional[InvoiceDiscountAllocationMethod] = None
    invoice_tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    reason: Optional[str] = Field(default=None, max_length=500)
    version: Optional[int] = Field(default=None, ge=1)


class PurchaseItemPatch(BaseModel):
    product_id: Optional[UUID] = None
    matched_product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    brand_name: Optional[str] = Field(default=None, max_length=120)
    category_name: Optional[str] = Field(default=None, max_length=120)
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=180)
    proposed_product_name: Optional[str] = Field(default=None, min_length=1, max_length=180)
    barcode: Optional[str] = Field(default=None, max_length=80)
    supplier_product_code: Optional[str] = Field(default=None, max_length=120)
    internal_sku: Optional[str] = Field(default=None, max_length=120)
    style_code: Optional[str] = Field(default=None, max_length=80)
    hsn_sac: Optional[str] = Field(default=None, max_length=40)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=40)
    size: Optional[str] = Field(default=None, max_length=60)
    color: Optional[str] = Field(default=None, max_length=80)
    quantity: Optional[int] = Field(default=None, gt=0)
    purchase_price: Optional[Decimal] = Field(default=None, ge=0)
    discount: Optional[Decimal] = Field(default=None, ge=0)
    list_unit_price: Optional[Decimal] = Field(default=None, ge=0)
    invoiced_unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_type: Optional[PurchaseItemDiscountType] = None
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=100)
    discount_per_unit: Optional[Decimal] = Field(default=None, ge=0)
    discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    discount_reason: Optional[str] = Field(default=None, max_length=500)
    discount_source: Optional[DiscountSource] = None
    free_quantity: Optional[Decimal] = Field(default=None, ge=0)
    chargeable_quantity: Optional[Decimal] = Field(default=None, ge=0)
    accepted_quantity: Optional[Decimal] = Field(default=None, ge=0)
    promotion_id: Optional[UUID] = None
    discount_rule_id: Optional[UUID] = None
    discount_verified: Optional[bool] = None
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)
    mrp: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    match_status: Optional[str] = Field(default=None, max_length=40)
    batch_number: Optional[str] = Field(default=None, max_length=120)
    manufacturing_date: Optional[date_type] = None
    expiry_date: Optional[date_type] = None
    create_new_product: Optional[bool] = None
    variant_attributes: Optional[dict[str, str]] = None
    classification_verified: Optional[bool] = None
    reason: Optional[str] = Field(default=None, max_length=500)
    version: Optional[int] = Field(default=None, ge=1)


class PurchaseItemRead(PurchaseItemReview, ORMBaseModel):
    id: UUID


class PurchaseRead(ORMBaseModel):
    id: UUID
    store_id: Optional[UUID]
    supplier_id: Optional[UUID]
    uploaded_file_id: Optional[UUID]
    purchase_document_id: Optional[UUID]
    processing_job_id: Optional[UUID]
    invoice_number: Optional[str]
    purchase_date: date_type
    invoice_date: Optional[date_type]
    received_date: Optional[date_type]
    due_date: Optional[date_type]
    supplier_name: Optional[str]
    payment_mode: str
    amount_paid: Decimal
    place_of_supply: Optional[str]
    purchase_reference: Optional[str]
    notes: Optional[str]
    warehouse: Optional[str]
    currency: str
    status: PurchaseStatus
    extracted_payload: dict
    reviewed_payload: dict
    subtotal: Decimal
    discount: Decimal
    invoice_discount_type: str
    invoice_discount_percentage: Decimal
    invoice_discount_amount: Decimal
    invoice_discount_reason: Optional[str]
    invoice_discount_allocation_method: str
    invoice_tax_rate: Decimal
    tax_amount: Decimal
    packaging_amount: Decimal
    freight_amount: Decimal
    round_off: Decimal
    total_amount: Decimal
    image_hash: Optional[str]
    ai_processing_status: str
    version: int
    workflow_status: str
    total_quantity: Decimal
    balance_due: Decimal
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseItemRead] = Field(default_factory=list)


class PurchaseSupplierRead(BaseModel):
    id: UUID
    name: str
    gst_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PurchaseDocumentRead(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    sha256: str


class PurchaseAuditRead(BaseModel):
    id: UUID
    action: str
    reason: Optional[str] = None
    before_data: Optional[dict] = None
    after_data: Optional[dict] = None
    performed_by: Optional[str] = None
    created_at: datetime


class PurchaseDetailRead(PurchaseRead):
    supplier: Optional[PurchaseSupplierRead] = None
    document: Optional[PurchaseDocumentRead] = None
    processing_job: Optional["DocumentJobRead"] = None
    audit_history: list[PurchaseAuditRead] = Field(default_factory=list)


class PurchaseValidationRead(BaseModel):
    valid: bool
    messages: list[str] = Field(default_factory=list)
    errors: list["PurchaseValidationError"] = Field(default_factory=list)
    subtotal: Decimal
    discount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class PurchaseValidationError(BaseModel):
    code: str
    purchase_item_id: Optional[UUID] = None
    field: Optional[str] = None
    message: str


class PurchaseItemClassificationPatch(BaseModel):
    item_ids: list[UUID] = Field(min_length=1)
    matched_product_id: Optional[UUID] = None
    proposed_product_name: Optional[str] = Field(default=None, min_length=1, max_length=180)
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    create_new_product: bool
    reason: Optional[str] = Field(default=None, max_length=500)
    version: Optional[int] = Field(default=None, ge=1)


class PurchaseCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    version: Optional[int] = Field(default=None, ge=1)


class PurchaseUploadResponse(BaseModel):
    purchase: PurchaseRead
    extracted_invoice: ExtractedInvoice
    review_items: list[PurchaseItemReview]
    duplicate_warning: Optional[str] = None


class PurchaseDocumentAccepted(BaseModel):
    document_id: UUID
    job_id: UUID
    status: DocumentJobStatus
    request_id: str
    duplicate: bool = False


class DocumentJobRead(ORMBaseModel):
    id: UUID
    document_id: UUID
    status: DocumentJobStatus
    progress: int
    message: str
    request_id: str
    provider_name: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None


class PurchaseFromDocumentCreate(BaseModel):
    job_id: UUID


PurchaseDetailRead.model_rebuild()
PurchaseValidationRead.model_rebuild()

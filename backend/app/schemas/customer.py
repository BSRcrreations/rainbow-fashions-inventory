from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMBaseModel
from app.services.customer_phone import normalize_customer_phone


class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    phone: Optional[str] = Field(default=None, max_length=30)
    alternate_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    opening_credit: Decimal = Field(default=Decimal("0"), ge=0)
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    is_active: bool = True
    sms_opt_out: bool = False
    sms_suppression_reason: Optional[str] = Field(default=None, max_length=300)

    @field_validator("name", "alternate_phone", "gst_number", "city", "state", "postal_code", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_customer_phone(value)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    phone: Optional[str] = Field(default=None, max_length=30)
    alternate_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    opening_credit: Optional[Decimal] = Field(default=None, ge=0)
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    sms_opt_out: Optional[bool] = None
    sms_suppression_reason: Optional[str] = Field(default=None, max_length=300)

    @field_validator("name", "alternate_phone", "gst_number", "city", "state", "postal_code", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        return normalize_customer_phone(value)


class CustomerPaymentCreate(BaseModel):
    payment_date: Optional[datetime] = None
    amount: Decimal = Field(gt=0)
    payment_mode: str = Field(min_length=2, max_length=40)
    reference: Optional[str] = Field(default=None, max_length=140)
    notes: Optional[str] = None

    @field_validator("payment_mode", "reference", mode="before")
    @classmethod
    def normalize_payment_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class CustomerPaymentRead(CustomerPaymentCreate, ORMBaseModel):
    id: UUID
    customer_id: UUID
    store_id: UUID
    created_by: Optional[UUID]
    created_at: datetime


class CustomerRead(CustomerBase, ORMBaseModel):
    # Read existing records without imposing the stricter minimum that applies
    # to new customer creation.  Historical data can contain a one-character
    # name and should remain visible/editable rather than breaking the list.
    name: str = Field(min_length=1, max_length=180)
    id: UUID
    store_id: UUID
    credit_sales_total: Decimal = Decimal("0")
    paid_total: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
    sms_opted_out_at: Optional[datetime] = None
    last_sms_sent_at: Optional[datetime] = None
    last_purchase_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CustomerLedgerEntry(BaseModel):
    id: UUID
    entry_type: str
    entry_date: datetime
    reference: Optional[str]
    description: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal


class CustomerDetailRead(CustomerRead):
    payments: list[CustomerPaymentRead] = Field(default_factory=list)
    ledger: list[CustomerLedgerEntry] = Field(default_factory=list)

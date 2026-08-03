from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMBaseModel


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    contact_person: Optional[str] = Field(default=None, max_length=140)
    phone: Optional[str] = Field(default=None, max_length=30)
    alternate_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(default=None, max_length=40)
    pan_number: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    is_active: bool = True

    @field_validator("name", "contact_person", "phone", "alternate_phone", "gst_number", "pan_number", "city", "state", "postal_code", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    contact_person: Optional[str] = Field(default=None, max_length=140)
    phone: Optional[str] = Field(default=None, max_length=30)
    alternate_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(default=None, max_length=40)
    pan_number: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    opening_balance: Optional[Decimal] = Field(default=None, ge=0)
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name", "contact_person", "phone", "alternate_phone", "gst_number", "pan_number", "city", "state", "postal_code", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SupplierPaymentCreate(BaseModel):
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


class SupplierPaymentRead(SupplierPaymentCreate, ORMBaseModel):
    id: UUID
    supplier_id: UUID
    store_id: UUID
    created_by: Optional[UUID]
    created_at: datetime


class SupplierRead(SupplierBase, ORMBaseModel):
    id: UUID
    store_id: Optional[UUID]
    purchase_total: Decimal = Decimal("0")
    paid_total: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime


class SupplierLedgerEntry(BaseModel):
    id: UUID
    entry_type: str
    entry_date: datetime
    reference: Optional[str]
    description: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal


class SupplierDetailRead(SupplierRead):
    payments: list[SupplierPaymentRead] = Field(default_factory=list)
    ledger: list[SupplierLedgerEntry] = Field(default_factory=list)

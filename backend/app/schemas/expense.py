from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBaseModel


class ExpenseCategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: Optional[str] = None
    is_active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class ExpenseCategoryRead(ExpenseCategoryBase, ORMBaseModel):
    id: UUID
    store_id: UUID
    created_at: datetime
    updated_at: datetime


class ExpenseBase(BaseModel):
    category_id: UUID
    expense_date: date
    title: str = Field(min_length=2, max_length=180)
    vendor: Optional[str] = Field(default=None, max_length=180)
    amount: Decimal = Field(gt=0)
    payment_mode: str = Field(min_length=2, max_length=40)
    reference: Optional[str] = Field(default=None, max_length=140)
    notes: Optional[str] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("title", "vendor", "payment_mode", "reference", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category_id: Optional[UUID] = None
    expense_date: Optional[date] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    vendor: Optional[str] = Field(default=None, max_length=180)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    payment_mode: Optional[str] = Field(default=None, min_length=2, max_length=40)
    reference: Optional[str] = Field(default=None, max_length=140)
    notes: Optional[str] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("title", "vendor", "payment_mode", "reference", mode="before")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class ExpenseRead(ExpenseBase, ORMBaseModel):
    id: UUID
    store_id: UUID
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    category: Optional[ExpenseCategoryRead] = None

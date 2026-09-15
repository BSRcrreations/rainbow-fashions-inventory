from __future__ import annotations

from typing import Optional

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import UserRole
from app.schemas.common import ORMBaseModel


class ReceiptSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    printer_type: Literal["BROWSER"] = "BROWSER"
    width_mm: Literal[80, 58] = 80
    margin_mm: float = Field(default=3, ge=0, le=10)
    copies: int = Field(default=1, ge=1, le=5)
    show_gst: bool = False
    tax_mode: Literal["INTRA_STATE", "INTER_STATE"] = "INTRA_STATE"
    return_policy: str = Field(default="Please keep your bill for returns and exchanges.", max_length=300)
    thank_you: str = Field(default="Thank you for shopping with Rainbow Fashions!", max_length=180)


class LabelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    printer_type: Literal["BROWSER"] = "BROWSER"
    width_mm: int = Field(default=50, ge=20, le=120)
    height_mm: int = Field(default=30, ge=15, le=100)
    margin_mm: float = Field(default=2, ge=0, le=8)
    copies: int = Field(default=1, ge=1, le=100)
    show_product_name: bool = True
    show_size: bool = True
    show_mrp: bool = True
    show_barcode_number: bool = True

    @model_validator(mode="after")
    def printable_area(self):
        if self.margin_mm * 2 >= min(self.width_mm, self.height_mm) - 8:
            raise ValueError("Choose smaller margins to leave room for the barcode.")
        return self


class PrinterSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt: ReceiptSettings = Field(default_factory=ReceiptSettings)
    label: LabelSettings = Field(default_factory=LabelSettings)


class StoreSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="Rainbow Fashions", min_length=2, max_length=120)
    address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=30)
    gstin: str = Field(default="", max_length=40)
    logo_url: str = Field(default="", max_length=500)
    timezone: str = "Asia/Kolkata"
    cashier_max_discount_percent: Decimal = Field(default=Decimal("10"), ge=0, le=100, max_digits=5, decimal_places=2)
    require_payment_reference: bool = False
    receipt: ReceiptSettings = Field(default_factory=ReceiptSettings)
    label: LabelSettings = Field(default_factory=LabelSettings)

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Choose a valid time zone, such as Asia/Kolkata.")
        return value

    @field_validator("logo_url")
    @classmethod
    def safe_logo(cls, value):
        if value and not value.startswith("/uploads/products/"):
            raise ValueError("Use an image uploaded to this shop.")
        return value


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.CASHIER

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120)
    role: UserRole
    is_active: bool
    reason: str = Field(min_length=3, max_length=500)


class DayClosingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_date: date
    opening_cash: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    actual_cash: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    notes: Optional[str] = Field(default=None, max_length=500)


class DayClosingSummary(BaseModel):
    business_date: date
    timezone: str
    opening_cash: Decimal
    cash_sales: Decimal
    cash_refunds: Decimal
    cash_expenses: Decimal
    customer_cash_payments: Decimal
    supplier_cash_payments: Decimal = Decimal("0")
    expected_cash: Decimal
    payment_totals: dict[str, Decimal]
    bills: int


class DayClosingRead(ORMBaseModel):
    id: UUID
    business_date: date
    opening_cash: Decimal
    actual_cash: Decimal
    expected_cash: Decimal
    difference: Decimal
    summary_json: dict
    status: str
    notes: Optional[str]
    created_by: Optional[UUID]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime


class AuditRead(BaseModel):
    id: str
    created_at: datetime
    action: str
    actor: str
    reference: Optional[str] = None
    reason: Optional[str] = None
    before_data: Optional[dict] = None
    after_data: Optional[dict] = None
    request_id: Optional[str] = None


class AuditPage(BaseModel):
    items: list[AuditRead]
    has_more: bool

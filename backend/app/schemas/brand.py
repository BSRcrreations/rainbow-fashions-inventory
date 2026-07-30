from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBaseModel


class BrandBase(BaseModel):
    category_id: UUID
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        return value.strip()


class BrandRead(BrandBase, ORMBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime

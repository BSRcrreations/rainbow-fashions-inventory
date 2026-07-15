from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


class BrandBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    is_active: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BrandRead(BrandBase, ORMBaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime

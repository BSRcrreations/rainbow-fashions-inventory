from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import ORMBaseModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(ORMBaseModel):
    id: UUID
    store_id: Optional[UUID]
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

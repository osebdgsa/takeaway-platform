"""User request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    # No ``role`` field on purpose: public sign-up must never grant admin.
    # bcrypt only considers the first 72 bytes, so cap the input.
    password: str = Field(min_length=8, max_length=72)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None

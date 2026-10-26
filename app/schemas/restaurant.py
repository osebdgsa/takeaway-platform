"""Restaurant schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1)
    phone: str | None = Field(default=None, max_length=32)
    cuisine_type: str | None = Field(default=None, max_length=64)


class RestaurantCreate(RestaurantBase):
    model_config = ConfigDict(extra="forbid")


class RestaurantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, max_length=32)
    cuisine_type: str | None = Field(default=None, max_length=64)


class RestaurantRead(RestaurantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

"""Menu item schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    model_config = ConfigDict(extra="forbid")


class MenuItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    is_available: bool | None = None


class MenuItemRead(MenuItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    created_at: datetime
    updated_at: datetime

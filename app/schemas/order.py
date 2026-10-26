"""Order schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus


class OrderLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    menu_item_id: UUID
    quantity: int = Field(ge=1, le=99)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restaurant_id: UUID
    items: list[OrderLineCreate] = Field(min_length=1, max_length=50)


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus


class OrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: UUID | None
    menu_item_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    restaurant_id: UUID
    status: OrderStatus
    total_amount: Decimal
    ordered_at: datetime
    items: list[OrderLineRead]

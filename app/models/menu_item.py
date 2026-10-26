"""Menu item model."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.order import OrderItem
    from app.models.restaurant import Restaurant


class MenuItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_items"

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="menu_item")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MenuItem {self.name} {self.price}>"

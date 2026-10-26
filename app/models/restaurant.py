"""Restaurant model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.menu_item import MenuItem
    from app.models.order import Order


class Restaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    cuisine_type: Mapped[str | None] = mapped_column(String(64), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    menu_items: Mapped[list[MenuItem]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(back_populates="restaurant")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Restaurant {self.name}>"

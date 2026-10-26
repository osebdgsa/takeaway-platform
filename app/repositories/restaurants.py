"""Restaurant persistence."""

import uuid

from sqlalchemy import func, select

from app.models.order import Order
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository


class RestaurantRepository(BaseRepository[Restaurant]):
    model = Restaurant

    def paginate(self, *, limit: int, offset: int) -> tuple[list[Restaurant], int]:
        stmt = (
            select(Restaurant)
            .order_by(Restaurant.name.asc(), Restaurant.id.asc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self.db.scalars(stmt))
        total = self.db.scalar(select(func.count()).select_from(Restaurant)) or 0
        return items, total

    def create(self, **fields: object) -> Restaurant:
        return self.add(Restaurant(**fields))

    def has_orders(self, restaurant_id: uuid.UUID) -> bool:
        stmt = select(Order.id).where(Order.restaurant_id == restaurant_id).limit(1)
        return self.db.scalar(stmt) is not None

    def get_many(self, ids: set[uuid.UUID]) -> list[Restaurant]:
        if not ids:
            return []
        return list(self.db.scalars(select(Restaurant).where(Restaurant.id.in_(ids))))

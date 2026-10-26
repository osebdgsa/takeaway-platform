"""Menu item persistence."""

import uuid

from sqlalchemy import func, select

from app.models.menu_item import MenuItem
from app.repositories.base import BaseRepository


class MenuItemRepository(BaseRepository[MenuItem]):
    model = MenuItem

    def paginate_for_restaurant(
        self, restaurant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[MenuItem], int]:
        stmt = (
            select(MenuItem)
            .where(MenuItem.restaurant_id == restaurant_id)
            .order_by(MenuItem.name.asc(), MenuItem.id.asc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self.db.scalars(stmt))
        total = (
            self.db.scalar(
                select(func.count())
                .select_from(MenuItem)
                .where(MenuItem.restaurant_id == restaurant_id)
            )
            or 0
        )
        return items, total

    def get_many(self, ids: set[uuid.UUID]) -> list[MenuItem]:
        if not ids:
            return []
        return list(self.db.scalars(select(MenuItem).where(MenuItem.id.in_(ids))))

    def create(self, **fields: object) -> MenuItem:
        return self.add(MenuItem(**fields))

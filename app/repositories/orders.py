"""Order persistence with explicit eager loading of order lines."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.repositories.base import BaseRepository

_LOAD_LINES = selectinload(Order.items).selectinload(OrderItem.menu_item)


class OrderRepository(BaseRepository[Order]):
    model = Order

    def get_with_lines(self, order_id: uuid.UUID) -> Order | None:
        stmt = select(Order).options(_LOAD_LINES).where(Order.id == order_id)
        return self.db.scalar(stmt)

    def paginate(
        self,
        *,
        limit: int,
        offset: int,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[list[Order], int]:
        stmt = select(Order).options(_LOAD_LINES)
        count_stmt = select(func.count()).select_from(Order)
        if customer_id is not None:
            stmt = stmt.where(Order.customer_id == customer_id)
            count_stmt = count_stmt.where(Order.customer_id == customer_id)

        stmt = stmt.order_by(Order.ordered_at.desc(), Order.id.desc())
        items = list(self.db.scalars(stmt.limit(limit).offset(offset)))
        total = self.db.scalar(count_stmt) or 0
        return items, total

    def create(self, **fields: object) -> Order:
        return self.add(Order(**fields))

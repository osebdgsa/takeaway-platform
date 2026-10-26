"""Order placement and lifecycle rules."""

import uuid
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import ALLOWED_TRANSITIONS, OrderStatus, UserRole
from app.models.order import Order, OrderItem
from app.models.user import User
from app.repositories.menu_items import MenuItemRepository
from app.repositories.orders import OrderRepository
from app.repositories.restaurants import RestaurantRepository
from app.schemas.order import OrderCreate

_CENT = Decimal("0.01")


class OrderService:
    def __init__(self, db) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.restaurants = RestaurantRepository(db)
        self.menu_items = MenuItemRepository(db)

    # ------------------------------------------------------------------ read
    def list_for(
        self, user: User, *, limit: int, offset: int
    ) -> tuple[list[Order], int]:
        customer_id = None if user.role is UserRole.admin else user.id
        return self.orders.paginate(limit=limit, offset=offset, customer_id=customer_id)

    def get_for(
        self, user: User, order_id: uuid.UUID, *, for_update: bool = False
    ) -> Order:
        order = self.orders.get_with_lines(order_id, for_update=for_update)
        # Non-owners get 404 (not 403) so order ids cannot be probed.
        if order is None or (
            user.role is not UserRole.admin and order.customer_id != user.id
        ):
            raise NotFoundError("Order not found")
        return order

    # ----------------------------------------------------------------- write
    def create(self, customer: User, payload: OrderCreate) -> Order:
        restaurant = self.restaurants.get(payload.restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found")

        requested_ids = [line.menu_item_id for line in payload.items]
        if len(requested_ids) != len(set(requested_ids)):
            raise ValidationError("Duplicate menu items are not allowed")

        found = {item.id: item for item in self.menu_items.get_many(set(requested_ids))}
        missing = set(requested_ids) - found.keys()
        if missing:
            raise ValidationError(
                "Unknown menu item(s): "
                + ", ".join(sorted(str(item_id) for item_id in missing))
            )

        order = Order(
            customer_id=customer.id,
            restaurant_id=restaurant.id,
            status=OrderStatus.pending,
            total_amount=Decimal("0.00"),
        )
        total = Decimal("0.00")
        for line in payload.items:
            menu_item = found[line.menu_item_id]
            if menu_item.restaurant_id != restaurant.id:
                raise ValidationError(
                    f"Menu item '{menu_item.name}' does not belong to this restaurant"
                )
            if not menu_item.is_available:
                raise ConflictError(
                    f"Menu item '{menu_item.name}' is currently unavailable"
                )
            unit_price = Decimal(menu_item.price).quantize(_CENT)
            order.items.append(
                OrderItem(
                    menu_item_id=menu_item.id,
                    quantity=line.quantity,
                    unit_price=unit_price,
                )
            )
            total += unit_price * line.quantity

        order.total_amount = total.quantize(_CENT)
        self.orders.add(order)
        self.orders.commit()
        return self.orders.get_with_lines(order.id)  # type: ignore[return-value]

    def update_status(self, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
        order = self.orders.get_with_lines(order_id, for_update=True)
        if order is None:
            raise NotFoundError("Order not found")
        if new_status is order.status:
            return order  # idempotent
        allowed = ALLOWED_TRANSITIONS[order.status]
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot change order status from '{order.status.value}' "
                f"to '{new_status.value}'"
            )
        order.status = new_status
        self.orders.commit()
        return self.orders.get_with_lines(order.id)  # type: ignore[return-value]

    def cancel(self, customer: User, order_id: uuid.UUID) -> Order:
        order = self.get_for(customer, order_id, for_update=True)
        if order.status is not OrderStatus.pending:
            raise ConflictError("Only pending orders can be cancelled")
        order.status = OrderStatus.cancelled
        self.orders.commit()
        return self.orders.get_with_lines(order.id)  # type: ignore[return-value]

"""Import every model so that Base.metadata is complete for Alembic/tests."""

from app.models.enums import OrderStatus, UserRole
from app.models.idempotency_key import IdempotencyKey
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.models.refresh_token import RefreshToken
from app.models.restaurant import Restaurant
from app.models.user import User

__all__ = [
    "IdempotencyKey",
    "MenuItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "RefreshToken",
    "Restaurant",
    "User",
    "UserRole",
]

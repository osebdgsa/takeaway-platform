"""Order endpoints: customers place/track, admins advance status."""

import uuid

from fastapi import APIRouter, status

from app.controllers.deps import AdminUser, CurrentUser, DbSession, Limit, Offset
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services.orders import OrderService

router = APIRouter()


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order",
)
def place_order(payload: OrderCreate, db: DbSession, user: CurrentUser):
    return OrderService(db).create(user, payload)


@router.get(
    "",
    response_model=Page[OrderRead],
    summary="List orders (own orders, or all orders for admins)",
)
def list_orders(
    db: DbSession,
    user: CurrentUser,
    limit: Limit = 20,
    offset: Offset = 0,
):
    items, total = OrderService(db).list_for(user, limit=limit, offset=offset)
    return Page[OrderRead](
        items=[OrderRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderRead, summary="Track one order")
def get_order(order_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return OrderService(db).get_for(user, order_id)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancel a pending order (owner)",
)
def cancel_order(order_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return OrderService(db).cancel(user, order_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderRead,
    summary="Advance an order's status (admin)",
)
def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: DbSession,
    admin: AdminUser,
):
    return OrderService(db).update_status(order_id, payload.status)

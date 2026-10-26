"""Order endpoints: customers place/track, admins advance status."""

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.controllers.deps import AdminUser, CurrentUser, DbSession, Limit, Offset
from app.core.config import settings
from app.core.ratelimit import SlidingWindowLimiter
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services.orders import OrderService

router = APIRouter()

order_limiter = SlidingWindowLimiter(
    limit=settings.RATE_LIMIT_ORDERS, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)


def _order_rate_limit(request: Request, user: CurrentUser) -> None:
    """Apply a per-user sliding-window limit to order placement."""
    order_limiter.hit(str(user.id))


RateLimitedOrder = Depends(_order_rate_limit)


def _header_and_hash(request: Request, payload: OrderCreate) -> tuple[str, str]:
    """Return (idempotency_key, sha256-of-normalised-body)."""
    raw_key = request.headers.get("Idempotency-Key", "")
    key = raw_key.strip()
    body_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    return key, body_hash


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order (optionally with an Idempotency-Key header)",
)
def place_order(
    payload: OrderCreate,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: Annotated[None, RateLimitedOrder],
):
    key, body_hash = _header_and_hash(request, payload)
    return OrderService(db).create(
        user, payload, idempotency_key=key, request_hash=body_hash
    )


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

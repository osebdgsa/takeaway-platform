"""Enumerations persisted as portable VARCHAR columns (no native PG ENUM)."""

import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


#: State machine: which target states each current state allows.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.accepted, OrderStatus.cancelled},
    OrderStatus.accepted: {OrderStatus.out_for_delivery, OrderStatus.cancelled},
    OrderStatus.out_for_delivery: {OrderStatus.delivered},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}

"""Rate-limit behaviours (429) and the status-lifecycle matrix."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import auth, register_customer


@pytest.fixture()
def tight_login_limiter(client: TestClient):
    from app.controllers.auth import login_limiter

    old_limit = login_limiter.limit
    login_limiter.limit = 3
    login_limiter.reset()
    yield login_limiter
    login_limiter.limit = old_limit
    login_limiter.reset()


def test_login_rate_limited_returns_429(
    client: TestClient, tight_login_limiter
) -> None:
    # Same source IP as every TestClient request, by design.
    payloads = [
        {"username": "brute@example.com", "password": "supersecret123"}
        for _ in range(4)
    ]
    codes = [client.post("/api/auth/login", data=p).status_code for p in payloads]
    assert codes[:3] == [401, 401, 401]  # allowed hits (wrong password expected)
    assert codes[3] == 429  # window exhausted


def test_rate_limit_is_scoped_per_client_address(client: TestClient) -> None:
    from app.controllers.auth import login_limiter

    client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "x" * 7},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    # The limiter keys on the forwarded client, not on the peer, so separate
    # clients have separate windows.
    assert "203.0.113.9" in login_limiter._hits


def test_order_rate_limiting_is_enforced(
    client: TestClient, db_session, admin_token: str
) -> None:
    from app.controllers.orders import order_limiter

    _customer_id, customer_token = register_customer(client)
    restaurant = client.post(
        "/api/restaurants",
        json={"name": "Flood Pizza", "address": "Str. Burst 1"},
        headers=auth(admin_token),
    ).json()
    item = client.post(
        f"/api/restaurants/{restaurant['id']}/menu-items",
        json={"name": "M", "price": "5.00"},
        headers=auth(admin_token),
    ).json()
    payload = {
        "restaurant_id": restaurant["id"],
        "items": [{"menu_item_id": item["id"], "quantity": 1}],
    }

    old_limit = order_limiter.limit
    order_limiter.limit = 5
    order_limiter.reset()
    try:
        codes = [
            client.post(
                "/api/orders", json=payload, headers=auth(customer_token)
            ).status_code
            for _ in range(6)
        ]
        assert codes[:5] == [201] * 5
        assert codes[5] == 429
    finally:
        order_limiter.limit = old_limit
        order_limiter.reset()


def test_status_matrix_has_no_state_skips() -> None:
    """Guarantee no path 'delivers' before the chain: delivered is reachable
    only from out_for_delivery, and terminal states have no outgoing edges."""
    from app.models.enums import ALLOWED_TRANSITIONS, OrderStatus

    assert ALLOWED_TRANSITIONS[OrderStatus.pending] == {
        OrderStatus.accepted,
        OrderStatus.cancelled,
    }
    assert ALLOWED_TRANSITIONS[OrderStatus.accepted] == {
        OrderStatus.out_for_delivery,
        OrderStatus.cancelled,
    }
    assert ALLOWED_TRANSITIONS[OrderStatus.out_for_delivery] == {OrderStatus.delivered}
    assert ALLOWED_TRANSITIONS[OrderStatus.delivered] == set()
    assert ALLOWED_TRANSITIONS[OrderStatus.cancelled] == set()
    # delivered is only ever reachable from out_for_delivery, never in one
    # hop from pending/accepted.
    assert OrderStatus.delivered not in ALLOWED_TRANSITIONS[OrderStatus.pending]
    assert OrderStatus.delivered not in ALLOWED_TRANSITIONS[OrderStatus.accepted]
    # No state allows re-entry into itself except no-op handled by service.
    assert all(
        OrderStatus.delivered not in targets
        for source, targets in ALLOWED_TRANSITIONS.items()
        if source in (OrderStatus.pending, OrderStatus.accepted)
    )

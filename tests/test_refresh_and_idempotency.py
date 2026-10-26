"""Refresh-token rotation, revocation and idempotency-key behaviours."""

from fastapi.testclient import TestClient
from tests.conftest import add_menu_item, auth, register_customer


def _pair(client: TestClient, email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _register_pair(client: TestClient, email: str = "customer@example.com") -> dict:
    register_customer(client, email=email)
    return _pair(client, email, "supersecret123")


def _make_menu(client: TestClient, admin_token: str) -> dict:
    restaurant = client.post(
        "/api/restaurants",
        json={"name": "Idempotent Pizza", "address": "Str. Retry 7"},
        headers=auth(admin_token),
    ).json()
    item = add_menu_item(client, admin_token, restaurant["id"], price="10.00")
    return {"restaurant": restaurant, "item": item}


def test_login_and_refresh_return_both_tokens(client: TestClient) -> None:
    body = _register_pair(client)
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] == 15 * 60

    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new = refreshed.json()
    assert new["access_token"] != body["access_token"]
    assert new["refresh_token"] != body["refresh_token"]


def test_refresh_rotation_invalidates_the_old_pair(client: TestClient) -> None:
    body = _register_pair(client)
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
        ).status_code
        == 200
    )

    replay = client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert replay.status_code == 401


def test_refresh_reuse_revokes_the_whole_family(client: TestClient) -> None:
    body = _register_pair(client)
    # Rotate once: the original refresh token is now revoked.
    rotated = client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    ).json()
    assert rotated["access_token"]

    # Replay the *revoked* token: every token for this user gets burned.
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
        ).status_code
        == 401
    )
    # The previously valid rotated pair must be dead as well.
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 401
    )


def test_garbage_refresh_token_is_401(client: TestClient) -> None:
    assert (
        client.post(
            "/api/auth/refresh", json={"refresh_token": "not-a-real-token"}
        ).status_code
        == 401
    )


def test_idempotency_key_replays_the_same_order(
    client: TestClient, admin_token: str
) -> None:
    _customer_id, customer_token = register_customer(client)
    menu = _make_menu(client, admin_token)
    payload = {
        "restaurant_id": menu["restaurant"]["id"],
        "items": [{"menu_item_id": menu["item"]["id"], "quantity": 1}],
    }

    first = client.post(
        "/api/orders",
        json=payload,
        headers={**auth(customer_token), "Idempotency-Key": "retry-1"},
    )
    second = client.post(
        "/api/orders",
        json=payload,
        headers={**auth(customer_token), "Idempotency-Key": "retry-1"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    # Keys are scoped per user: another customer may reuse the same value.
    _other_id, other_token = register_customer(client, email="other@example.com")
    third = client.post(
        "/api/orders",
        json=payload,
        headers={**auth(other_token), "Idempotency-Key": "retry-1"},
    )
    assert third.status_code == 201
    assert third.json()["id"] != first.json()["id"]


def test_idempotency_key_with_different_payload_is_409(
    client: TestClient, admin_token: str
) -> None:
    _customer_id, customer_token = register_customer(client)
    menu = _make_menu(client, admin_token)
    item = menu["item"]["id"]
    payload = {
        "restaurant_id": menu["restaurant"]["id"],
        "items": [{"menu_item_id": item, "quantity": 2}],
    }
    first = client.post(
        "/api/orders",
        json=payload,
        headers={**auth(customer_token), "Idempotency-Key": "k"},
    )
    changed = client.post(
        "/api/orders",
        json={**payload, "items": [{"menu_item_id": item, "quantity": 3}]},
        headers={**auth(customer_token), "Idempotency-Key": "k"},
    )
    assert first.status_code == 201
    assert changed.status_code == 409


def test_orders_without_key_behave_as_before(
    client: TestClient, admin_token: str
) -> None:
    _customer_id, customer_token = register_customer(client)
    menu = _make_menu(client, admin_token)
    payload = {
        "restaurant_id": menu["restaurant"]["id"],
        "items": [{"menu_item_id": menu["item"]["id"], "quantity": 1}],
    }
    first = client.post("/api/orders", json=payload, headers=auth(customer_token))
    second = client.post("/api/orders", json=payload, headers=auth(customer_token))
    assert first.status_code == 201 and second.status_code == 201, (
        first.text,
        second.text,
    )
    assert first.json()["id"] != second.json()["id"]

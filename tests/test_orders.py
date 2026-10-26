"""Order lifecycle, totals, ownership and RBAC tests."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from tests.conftest import add_menu_item, auth, register_customer


def _setup_menu(client: TestClient, admin_token: str) -> dict:
    restaurant = client.post(
        "/api/restaurants",
        json={"name": "Pizza Place", "address": "Str. Mare 5"},
        headers=auth(admin_token),
    ).json()
    margherita = add_menu_item(
        client, admin_token, restaurant["id"], name="Margherita", price="9.50"
    )
    diavola = add_menu_item(
        client, admin_token, restaurant["id"], name="Diavola", price="11.00"
    )
    return {"restaurant": restaurant, "margherita": margherita, "diavola": diavola}


def _place_order(client: TestClient, token: str, setup: dict, **overrides) -> dict:
    payload = {
        "restaurant_id": setup["restaurant"]["id"],
        "items": [
            {"menu_item_id": setup["margherita"]["id"], "quantity": 2},
            {"menu_item_id": setup["diavola"]["id"], "quantity": 1},
        ],
    }
    payload.update(overrides)
    response = client.post("/api/orders", json=payload, headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def menu(client: TestClient, admin_token: str) -> dict:
    return _setup_menu(client, admin_token)


def test_place_order_snapshots_prices_and_computes_total(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    assert order["status"] == "pending"
    assert Decimal(order["total_amount"]) == Decimal("30.00")
    assert len(order["items"]) == 2
    line = next(i for i in order["items"] if i["menu_item_name"] == "Margherita")
    assert Decimal(line["unit_price"]) == Decimal("9.50")
    assert Decimal(line["line_total"]) == Decimal("19.00")


def test_existing_order_is_unaffected_by_later_menu_edits(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    client.patch(
        f"/api/menu-items/{menu['margherita']['id']}",
        json={"price": "99.00"},
        headers=auth(admin_token),
    )

    refetched = client.get(
        f"/api/orders/{order['id']}", headers=auth(customer_token)
    ).json()
    assert Decimal(refetched["total_amount"]) == Decimal("30.00")


def test_customer_only_sees_own_orders(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)
    _, other_token = register_customer(client, email="other@example.com")

    assert (
        client.get(f"/api/orders/{order['id']}", headers=auth(other_token)).status_code
        == 404
    )
    listing = client.get("/api/orders", headers=auth(other_token)).json()
    assert listing["total"] == 0


def test_admin_sees_all_orders(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    listing = client.get("/api/orders", headers=auth(admin_token)).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == order["id"]

    fetched = client.get(f"/api/orders/{order['id']}", headers=auth(admin_token))
    assert fetched.status_code == 200


def test_full_status_workflow(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    for target in ("accepted", "out_for_delivery", "delivered"):
        response = client.patch(
            f"/api/orders/{order['id']}/status",
            json={"status": target},
            headers=auth(admin_token),
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target


def test_invalid_status_transition_is_rejected(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    response = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "delivered"},
        headers=auth(admin_token),
    )

    assert response.status_code == 409
    assert "cannot change order status" in response.json()["detail"].lower()


def test_status_update_is_idempotent(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    response = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "pending"},
        headers=auth(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_delivered_order_cannot_be_cancelled(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)
    for target in ("accepted", "out_for_delivery", "delivered"):
        client.patch(
            f"/api/orders/{order['id']}/status",
            json={"status": target},
            headers=auth(admin_token),
        )

    response = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers=auth(admin_token),
    )
    assert response.status_code == 409


def test_customer_cancels_pending_order(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    response = client.post(
        f"/api/orders/{order['id']}/cancel", headers=auth(customer_token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    again = client.post(
        f"/api/orders/{order['id']}/cancel", headers=auth(customer_token)
    )
    assert again.status_code == 409


def test_cannot_cancel_accepted_order(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)
    client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "accepted"},
        headers=auth(admin_token),
    )

    response = client.post(
        f"/api/orders/{order['id']}/cancel", headers=auth(customer_token)
    )
    assert response.status_code == 409


def test_unavailable_item_is_rejected(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    client.patch(
        f"/api/menu-items/{menu['diavola']['id']}",
        json={"is_available": False},
        headers=auth(admin_token),
    )

    response = client.post(
        "/api/orders",
        json={
            "restaurant_id": menu["restaurant"]["id"],
            "items": [{"menu_item_id": menu["diavola"]["id"], "quantity": 1}],
        },
        headers=auth(customer_token),
    )
    assert response.status_code == 409


def test_item_from_another_restaurant_is_rejected(
    client: TestClient, customer_token: str, admin_token: str, menu: dict
) -> None:
    other = client.post(
        "/api/restaurants",
        json={"name": "Other", "address": "Elsewhere 1"},
        headers=auth(admin_token),
    ).json()
    foreign_item = add_menu_item(
        client, admin_token, other["id"], name="Foreign", price="1.00"
    )

    response = client.post(
        "/api/orders",
        json={
            "restaurant_id": menu["restaurant"]["id"],
            "items": [{"menu_item_id": foreign_item["id"], "quantity": 1}],
        },
        headers=auth(customer_token),
    )
    assert response.status_code == 422


def test_duplicate_lines_are_rejected(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    item_id = menu["margherita"]["id"]
    response = client.post(
        "/api/orders",
        json={
            "restaurant_id": menu["restaurant"]["id"],
            "items": [
                {"menu_item_id": item_id, "quantity": 1},
                {"menu_item_id": item_id, "quantity": 2},
            ],
        },
        headers=auth(customer_token),
    )
    assert response.status_code == 422


def test_unknown_item_is_rejected(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    response = client.post(
        "/api/orders",
        json={
            "restaurant_id": menu["restaurant"]["id"],
            "items": [
                {
                    "menu_item_id": "00000000-0000-0000-0000-000000000000",
                    "quantity": 1,
                }
            ],
        },
        headers=auth(customer_token),
    )
    assert response.status_code == 422


def test_order_requires_at_least_one_line(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    response = client.post(
        "/api/orders",
        json={"restaurant_id": menu["restaurant"]["id"], "items": []},
        headers=auth(customer_token),
    )
    assert response.status_code == 422


def test_customer_cannot_update_status(
    client: TestClient, customer_token: str, menu: dict
) -> None:
    order = _place_order(client, customer_token, menu)

    response = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "accepted"},
        headers=auth(customer_token),
    )
    assert response.status_code == 403


def test_anonymous_cannot_place_order(client: TestClient, menu: dict) -> None:
    response = client.post(
        "/api/orders",
        json={"restaurant_id": menu["restaurant"]["id"], "items": []},
    )
    assert response.status_code == 401

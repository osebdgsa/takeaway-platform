"""Restaurant and menu management tests, including RBAC."""

from fastapi.testclient import TestClient
from tests.conftest import add_menu_item, auth

NEW_RESTAURANT = {
    "name": "Sushi Bar",
    "address": "Bd. Unirii 10",
    "phone": "+40700333444",
    "cuisine_type": "Japanese",
}


def test_list_restaurants_is_public_and_paginated(
    client: TestClient, admin_token: str
) -> None:
    for suffix in ("A", "B", "C"):
        payload = {**NEW_RESTAURANT, "name": f"Place {suffix}"}
        assert (
            client.post(
                "/api/restaurants", json=payload, headers=auth(admin_token)
            ).status_code
            == 201
        )

    response = client.get("/api/restaurants", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2

    page_two = client.get("/api/restaurants", params={"limit": 2, "offset": 2})
    assert len(page_two.json()["items"]) == 1


def test_restaurant_create_requires_admin(
    client: TestClient, customer_token: str
) -> None:
    response = client.post(
        "/api/restaurants", json=NEW_RESTAURANT, headers=auth(customer_token)
    )
    assert response.status_code == 403


def test_restaurant_create_requires_auth(client: TestClient) -> None:
    assert client.post("/api/restaurants", json=NEW_RESTAURANT).status_code == 401


def test_admin_creates_restaurant_owned_by_self(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        "/api/restaurants", json=NEW_RESTAURANT, headers=auth(admin_token)
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == NEW_RESTAURANT["name"]

    me = client.get("/api/auth/me", headers=auth(admin_token)).json()
    assert body["owner_id"] == me["id"]


def test_get_unknown_restaurant_is_404(client: TestClient) -> None:
    response = client.get("/api/restaurants/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_admin_updates_and_deletes_restaurant(
    client: TestClient, admin_token: str, restaurant: dict
) -> None:
    update = client.patch(
        f"/api/restaurants/{restaurant['id']}",
        json={"name": "Renamed", "phone": None},
        headers=auth(admin_token),
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed"
    assert update.json()["phone"] is None

    delete = client.delete(
        f"/api/restaurants/{restaurant['id']}", headers=auth(admin_token)
    )
    assert delete.status_code == 204
    assert client.get(f"/api/restaurants/{restaurant['id']}").status_code == 404


def test_customer_cannot_mutate_restaurants(
    client: TestClient, restaurant: dict, customer_token: str
) -> None:
    assert (
        client.patch(
            f"/api/restaurants/{restaurant['id']}",
            json={"name": "Hacked"},
            headers=auth(customer_token),
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/restaurants/{restaurant['id']}", headers=auth(customer_token)
        ).status_code
        == 403
    )


def test_menu_item_crud_and_public_listing(
    client: TestClient, admin_token: str, restaurant: dict
) -> None:
    margherita = add_menu_item(
        client, admin_token, restaurant["id"], name="Margherita", price="9.50"
    )
    add_menu_item(client, admin_token, restaurant["id"], name="Diavola", price="11.00")

    listing = client.get(f"/api/restaurants/{restaurant['id']}/menu-items")
    assert listing.status_code == 200
    assert listing.json()["total"] == 2

    single = client.get(f"/api/menu-items/{margherita['id']}")
    assert single.status_code == 200
    assert single.json()["price"] == "9.50"

    patched = client.patch(
        f"/api/menu-items/{margherita['id']}",
        json={"price": "10.00", "is_available": False},
        headers=auth(admin_token),
    )
    assert patched.status_code == 200
    assert patched.json()["price"] == "10.00"
    assert patched.json()["is_available"] is False

    removed = client.delete(
        f"/api/menu-items/{margherita['id']}", headers=auth(admin_token)
    )
    assert removed.status_code == 204
    assert client.get(f"/api/menu-items/{margherita['id']}").status_code == 404


def test_menu_item_writes_require_admin(
    client: TestClient, restaurant: dict, customer_token: str
) -> None:
    response = client.post(
        f"/api/restaurants/{restaurant['id']}/menu-items",
        json={"name": "Free pizza", "price": "0.01"},
        headers=auth(customer_token),
    )
    assert response.status_code == 403


def test_menu_item_rejects_invalid_price(
    client: TestClient, admin_token: str, restaurant: dict
) -> None:
    response = client.post(
        f"/api/restaurants/{restaurant['id']}/menu-items",
        json={"name": "Bad", "price": "0"},
        headers=auth(admin_token),
    )
    assert response.status_code == 422


def test_menu_items_for_unknown_restaurant_is_404(client: TestClient) -> None:
    response = client.get(
        "/api/restaurants/00000000-0000-0000-0000-000000000000/menu-items"
    )
    assert response.status_code == 404


def test_deleting_restaurant_removes_its_menu(
    client: TestClient, admin_token: str, restaurant: dict
) -> None:
    item = add_menu_item(client, admin_token, restaurant["id"])

    client.delete(f"/api/restaurants/{restaurant['id']}", headers=auth(admin_token))

    assert client.get(f"/api/menu-items/{item['id']}").status_code == 404

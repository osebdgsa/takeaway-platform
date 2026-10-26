"""Authentication and account-security tests."""

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from tests.conftest import auth, login, register_customer


def test_register_creates_customer(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "New.User@Example.com",
            "password": "supersecret123",
            "full_name": "New User",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new.user@example.com"  # normalised
    assert body["role"] == "customer"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    register_customer(client, email="dup@example.com")

    response = client.post(
        "/api/auth/register",
        json={
            "email": "DUP@example.com",
            "password": "supersecret123",
            "full_name": "Duplicate",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_cannot_self_assign_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": "supersecret123",
            "full_name": "Sneaky",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short",
        },
    )
    assert response.status_code == 422


def test_login_and_me(client: TestClient) -> None:
    customer_id, token = register_customer(client, email="me@example.com")

    response = client.get("/api/auth/me", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["id"] == customer_id


def test_login_wrong_password_is_401(client: TestClient) -> None:
    register_customer(client, email="wrong@example.com")
    response = client.post(
        "/api/auth/login",
        data={"username": "wrong@example.com", "password": "nope-nope-nope"},
    )
    assert response.status_code == 401


def test_login_unknown_email_matches_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        data={"username": "ghost@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_disabled_account_is_403(client: TestClient, db_session) -> None:
    user = User(
        email="disabled@example.com",
        hashed_password=hash_password("supersecret123"),
        full_name="Disabled",
        role=UserRole.customer,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": "disabled@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 403


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers=auth("not-a-jwt"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_login_token_is_reusable_and_role_aware(client: TestClient, db_session) -> None:
    from tests.conftest import create_admin

    create_admin(db_session, email="adm@example.com")
    token = login(client, "adm@example.com", "adminsecret123")
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.json()["role"] == "admin"

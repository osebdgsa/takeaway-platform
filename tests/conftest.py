"""Shared fixtures. Tests run on an in-memory SQLite DB for speed/isolation."""

import os

# Keep bcrypt cheap in tests; must be set before app settings are imported.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_rate_limiters() -> Iterator[None]:
    """Rate-limit state lives in-process and must not leak across tests."""
    from app.controllers.auth import login_limiter
    from app.controllers.orders import order_limiter

    login_limiter.reset()
    order_limiter.reset()
    yield
    login_limiter.reset()
    order_limiter.reset()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --------------------------------------------------------------------- helpers
def login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_customer(
    client: TestClient,
    email: str = "customer@example.com",
    password: str = "supersecret123",
) -> tuple[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Customer"},
    )
    assert response.status_code == 201, response.text
    customer_id = response.json()["id"]
    return customer_id, login(client, email, password)


def create_admin(db_session: Session, email: str = "admin@example.com") -> User:
    admin = User(
        email=email,
        hashed_password=hash_password("adminsecret123"),
        full_name="Test Admin",
        role=UserRole.admin,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture()
def admin_token(client: TestClient, db_session: Session) -> str:
    create_admin(db_session)
    return login(client, "admin@example.com", "adminsecret123")


@pytest.fixture()
def customer(client: TestClient) -> tuple[str, str]:
    return register_customer(client)


@pytest.fixture()
def customer_token(customer: tuple[str, str]) -> str:
    return customer[1]


@pytest.fixture()
def restaurant(client: TestClient, admin_token: str) -> dict:
    response = client.post(
        "/api/restaurants",
        json={
            "name": "Trattoria Roma",
            "address": "Via Roma 1",
            "phone": "+40700111222",
            "cuisine_type": "Italian",
        },
        headers=auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_menu_item(
    client: TestClient,
    admin_token: str,
    restaurant_id: str,
    *,
    name: str = "Margherita",
    price: str = "9.50",
    is_available: bool = True,
) -> dict:
    response = client.post(
        f"/api/restaurants/{restaurant_id}/menu-items",
        json={"name": name, "price": price, "is_available": is_available},
        headers=auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()

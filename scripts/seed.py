"""Seed demo data (idempotent).

Usage::

    python -m scripts.seed
"""

import sys
from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from sqlalchemy import select

DEMO_ITEMS = [
    ("Margherita", "Tomato, mozzarella, basil", "28.00"),
    ("Diavola", "Spicy salami, mozzarella", "34.00"),
    ("Quattro Formaggi", "Four cheeses", "36.00"),
]


def get_or_create_user(
    db,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        print(f"= user {email} already exists")
        return user
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    suffix = "" if is_active else " [disabled]"
    print(f"+ user {email} ({role.value}){suffix}")
    return user


def get_or_create_restaurant(db, owner: User) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.name == "Demo Pizzeria"))
    if restaurant is not None:
        print("= restaurant already exists")
        return restaurant
    restaurant = Restaurant(
        name="Demo Pizzeria",
        address="Str. Exemplu 1, Bucharest",
        phone="+40700000000",
        cuisine_type="Italian",
        owner_id=owner.id,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    print("+ restaurant Demo Pizzeria")
    return restaurant


def seed() -> None:
    with SessionLocal() as db:
        admin = get_or_create_user(
            db,
            email="admin@example.com",
            password="admin12345",
            full_name="Demo Admin",
            role=UserRole.admin,
        )
        get_or_create_user(
            db,
            email="customer@example.com",
            password="customer12345",
            full_name="Demo Customer",
            role=UserRole.customer,
        )
        get_or_create_user(
            db,
            email="customer2@example.com",
            password="customer212345",
            full_name="Second Customer",
            role=UserRole.customer,
        )
        get_or_create_user(
            db,
            email="blocked@example.com",
            password="blocked12345",
            full_name="Disabled Account",
            role=UserRole.customer,
            is_active=False,
        )
        restaurant = get_or_create_restaurant(db, admin)

        existing = set(
            db.scalars(
                select(MenuItem.name).where(MenuItem.restaurant_id == restaurant.id)
            )
        )
        for name, description, price in DEMO_ITEMS:
            if name in existing:
                print(f"= menu item {name} already exists")
                continue
            db.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    name=name,
                    description=description,
                    price=Decimal(price),
                    is_available=True,
                )
            )
            print(f"+ menu item {name}")
        db.commit()

    print("\nDone. Log in with:")
    print("  admin      admin@example.com     / admin12345")
    print("  customer   customer@example.com  / customer12345")
    print("  customer2  customer2@example.com / customer212345")
    print("  disabled   blocked@example.com   / blocked12345  -> 403 on login")


def main() -> int:
    seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Restaurant browsing (public) and management (admin) endpoints."""

import uuid

from fastapi import APIRouter, Response, status

from app.controllers.deps import AdminUser, DbSession, Limit, Offset
from app.schemas.common import Page
from app.schemas.menu_item import MenuItemCreate, MenuItemRead
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantRead,
    RestaurantUpdate,
)
from app.services.menu_items import MenuItemService
from app.services.restaurants import RestaurantService

router = APIRouter()


@router.get("", response_model=Page[RestaurantRead], summary="Browse restaurants")
def list_restaurants(db: DbSession, limit: Limit = 20, offset: Offset = 0):
    items, total = RestaurantService(db).list(limit=limit, offset=offset)
    return Page[RestaurantRead](
        items=[RestaurantRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{restaurant_id}",
    response_model=RestaurantRead,
    summary="Get one restaurant",
)
def get_restaurant(restaurant_id: uuid.UUID, db: DbSession):
    return RestaurantService(db).get_or_404(restaurant_id)


@router.get(
    "/{restaurant_id}/menu-items",
    response_model=Page[MenuItemRead],
    summary="Browse a restaurant menu",
)
def list_menu_items(
    restaurant_id: uuid.UUID,
    db: DbSession,
    limit: Limit = 20,
    offset: Offset = 0,
):
    items, total = MenuItemService(db).list_for_restaurant(
        restaurant_id, limit=limit, offset=offset
    )
    return Page[MenuItemRead](
        items=[MenuItemRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{restaurant_id}/menu-items",
    response_model=MenuItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a menu item to a restaurant (admin)",
)
def create_menu_item(
    restaurant_id: uuid.UUID,
    payload: MenuItemCreate,
    db: DbSession,
    admin: AdminUser,
):
    return MenuItemService(db).create(restaurant_id, payload)


@router.post(
    "",
    response_model=RestaurantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a restaurant (admin)",
)
def create_restaurant(payload: RestaurantCreate, db: DbSession, admin: AdminUser):
    return RestaurantService(db).create(payload, owner=admin)


@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantRead,
    summary="Update a restaurant (admin)",
)
def update_restaurant(
    restaurant_id: uuid.UUID,
    payload: RestaurantUpdate,
    db: DbSession,
    admin: AdminUser,
):
    return RestaurantService(db).update(restaurant_id, payload)


@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a restaurant and its menu (admin)",
)
def delete_restaurant(restaurant_id: uuid.UUID, db: DbSession, admin: AdminUser):
    RestaurantService(db).delete(restaurant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

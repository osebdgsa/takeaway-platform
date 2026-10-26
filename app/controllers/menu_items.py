"""Menu item endpoints: public read, admin write."""

import uuid

from fastapi import APIRouter, Response, status

from app.controllers.deps import AdminUser, DbSession
from app.schemas.menu_item import MenuItemRead, MenuItemUpdate
from app.services.menu_items import MenuItemService

router = APIRouter()


@router.get("/{menu_item_id}", response_model=MenuItemRead, summary="Get a menu item")
def get_menu_item(menu_item_id: uuid.UUID, db: DbSession):
    return MenuItemService(db).get_or_404(menu_item_id)


@router.patch(
    "/{menu_item_id}",
    response_model=MenuItemRead,
    summary="Update a menu item (admin)",
)
def update_menu_item(
    menu_item_id: uuid.UUID,
    payload: MenuItemUpdate,
    db: DbSession,
    admin: AdminUser,
):
    return MenuItemService(db).update(menu_item_id, payload)


@router.delete(
    "/{menu_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a menu item (admin)",
)
def delete_menu_item(menu_item_id: uuid.UUID, db: DbSession, admin: AdminUser):
    MenuItemService(db).delete(menu_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

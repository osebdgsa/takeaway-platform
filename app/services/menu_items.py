"""Menu business rules."""

import uuid

from app.core.exceptions import NotFoundError
from app.models.menu_item import MenuItem
from app.repositories.menu_items import MenuItemRepository
from app.repositories.restaurants import RestaurantRepository
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate


class MenuItemService:
    def __init__(self, db) -> None:
        self.db = db
        self.menu_items = MenuItemRepository(db)
        self.restaurants = RestaurantRepository(db)

    def _ensure_restaurant(self, restaurant_id: uuid.UUID) -> None:
        if self.restaurants.get(restaurant_id) is None:
            raise NotFoundError("Restaurant not found")

    def list_for_restaurant(
        self, restaurant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[MenuItem], int]:
        self._ensure_restaurant(restaurant_id)
        return self.menu_items.paginate_for_restaurant(
            restaurant_id, limit=limit, offset=offset
        )

    def get_or_404(self, menu_item_id: uuid.UUID) -> MenuItem:
        menu_item = self.menu_items.get(menu_item_id)
        if menu_item is None:
            raise NotFoundError("Menu item not found")
        return menu_item

    def create(self, restaurant_id: uuid.UUID, payload: MenuItemCreate) -> MenuItem:
        self._ensure_restaurant(restaurant_id)
        menu_item = self.menu_items.create(
            restaurant_id=restaurant_id, **payload.model_dump()
        )
        self.menu_items.commit()
        self.menu_items.refresh(menu_item)
        return menu_item

    def update(self, menu_item_id: uuid.UUID, payload: MenuItemUpdate) -> MenuItem:
        menu_item = self.get_or_404(menu_item_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(menu_item, field, value)
        if changes:
            self.menu_items.commit()
            self.menu_items.refresh(menu_item)
        return menu_item

    def delete(self, menu_item_id: uuid.UUID) -> None:
        menu_item = self.get_or_404(menu_item_id)
        self.menu_items.delete(menu_item)
        self.menu_items.commit()

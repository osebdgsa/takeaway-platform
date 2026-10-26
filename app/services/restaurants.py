"""Restaurant business rules."""

import uuid

from app.core.exceptions import NotFoundError
from app.models.restaurant import Restaurant
from app.models.user import User
from app.repositories.restaurants import RestaurantRepository
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


class RestaurantService:
    def __init__(self, db) -> None:
        self.db = db
        self.restaurants = RestaurantRepository(db)

    def list(self, *, limit: int, offset: int) -> tuple[list[Restaurant], int]:
        return self.restaurants.paginate(limit=limit, offset=offset)

    def get_or_404(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found")
        return restaurant

    def create(self, payload: RestaurantCreate, owner: User) -> Restaurant:
        restaurant = self.restaurants.create(owner_id=owner.id, **payload.model_dump())
        self.restaurants.commit()
        self.restaurants.refresh(restaurant)
        return restaurant

    def update(self, restaurant_id: uuid.UUID, payload: RestaurantUpdate) -> Restaurant:
        restaurant = self.get_or_404(restaurant_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(restaurant, field, value)
        if changes:
            self.restaurants.commit()
            self.restaurants.refresh(restaurant)
        return restaurant

    def delete(self, restaurant_id: uuid.UUID) -> None:
        restaurant = self.get_or_404(restaurant_id)
        self.restaurants.delete(restaurant)
        self.restaurants.commit()

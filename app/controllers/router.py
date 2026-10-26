"""Aggregate all HTTP routers."""

from fastapi import APIRouter

from app.controllers import auth, menu_items, orders, restaurants

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    restaurants.router, prefix="/restaurants", tags=["restaurants"]
)
api_router.include_router(menu_items.router, prefix="/menu-items", tags=["menu-items"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

"""Declarative base shared by every ORM model and Alembic."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata registry for the whole application."""

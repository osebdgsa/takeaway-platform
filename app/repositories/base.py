"""Thin persistence primitives. No business rules live here."""

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: object) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(self.model)) or 0

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, entity: ModelT) -> None:
        self.db.refresh(entity)

"""Idempotency key persistence for order placement."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey


class IdempotencyKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: uuid.UUID, key: str) -> IdempotencyKey | None:
        return self.db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.key == key
            )
        )

    def add(
        self,
        *,
        key: str,
        user_id: uuid.UUID,
        request_hash: str,
        order_id: uuid.UUID,
    ) -> IdempotencyKey:
        row = IdempotencyKey(
            key=key,
            user_id=user_id,
            request_hash=request_hash,
            order_id=order_id,
            first_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        return row

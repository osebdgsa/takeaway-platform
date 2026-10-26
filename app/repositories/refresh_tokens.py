"""Refresh token persistence and revocation."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken


def _aware(moment: datetime) -> datetime:
    """Normalize a datetime coming from the DB (SQLite drops tzinfo)."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def issue(
        self, user_id: uuid.UUID, *, now: datetime | None = None
    ) -> tuple[str, RefreshToken]:
        """Create a new opaque token; return (raw token, row)."""
        now = now or datetime.now(timezone.utc)
        raw = generate_refresh_token()
        row = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw),
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(row)
        return raw, row

    def get_active_by_hash(
        self, token_hash: str, *, now: datetime | None = None
    ) -> RefreshToken | None:
        now = now or datetime.now(timezone.utc)
        row = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if row is None:
            return None
        if row.revoked_at is not None or _aware(row.expires_at) <= now:
            return None
        return row

    def get_any_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    def revoke(self, row: RefreshToken, *, now: datetime | None = None) -> None:
        row.revoked_at = now or datetime.now(timezone.utc)
        self.db.add(row)

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        for row in self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        ):
            self.revoke(row, now=now)

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def rollback(self) -> None:
        self.db.rollback()

    def create(self, *, now: datetime | None = None, **fields: object) -> RefreshToken:
        row = RefreshToken(**fields)
        self.db.add(row)
        return row

"""Registration, authentication and token issuing (access + refresh)."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_tokens import RefreshTokenRepository, _aware
from app.repositories.users import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db) -> None:
        self.db = db
        self.users = UserRepository(db)
        self._refresh = RefreshTokenRepository(db)

    def register(self, payload: UserCreate) -> User:
        email = str(payload.email).strip().lower()
        if self.users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists")

        user = self.users.create(
            email=email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=UserRole.customer,
        )
        try:
            self.users.commit()
        except IntegrityError as exc:  # concurrent duplicate sign-up
            self.users.rollback()
            raise ConflictError("An account with this email already exists") from exc
        self.users.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.hashed_password):
            # Same message for unknown user and wrong password (no enumeration).
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise ForbiddenError("This account is disabled")
        return user

    def issue_token(self, user: User) -> Token:
        """Issue a fresh access + refresh pair (and persist the refresh row)."""
        access = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value},
        )
        raw_refresh, _row = self._refresh.issue(user.id)
        self.db.commit()
        return Token(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh(self, raw_refresh_token: str) -> Token:
        """Rotate the refresh token and issue a new access token.

        Presenting a previously *used* or *revoked* token is treated as a
        replay/leak signal: every remaining token for that user is revoked.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        row = self._refresh.get_any_by_hash(token_hash)
        now = datetime.now(timezone.utc)

        if row is None:
            raise UnauthorizedError("Invalid refresh token")

        was_revoked = row.revoked_at is not None
        expired = _aware(row.expires_at) <= now
        if was_revoked or expired:
            # Reuse of a rotated/revoked token: burn the whole family.
            self._refresh.revoke_all_for_user(row.user_id)
            self.db.commit()
            raise UnauthorizedError("Invalid refresh token")

        user = self.db.get(User, row.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid refresh token")

        self._refresh.revoke(row, now=now)
        return self.issue_token(user)

"""Shared FastAPI dependencies: DB session, current user, role guards."""

import uuid
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

DbSession = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    payload = decode_access_token(token)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError() from exc

    # Role and active flag come from the DB, never from the token, so a
    # demoted or disabled user loses access immediately.
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.admin:
        raise ForbiddenError("Admin privileges required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]

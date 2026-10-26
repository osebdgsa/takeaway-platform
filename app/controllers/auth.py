"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.controllers.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.ratelimit import SlidingWindowLimiter, client_ip, rate_limit
from app.schemas.auth import RefreshRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter()

login_limiter = SlidingWindowLimiter(
    limit=settings.RATE_LIMIT_LOGIN, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)
RateLimitedLogin = rate_limit(login_limiter, client_ip)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
)
def register(payload: UserCreate, db: DbSession) -> UserRead:
    user = AuthService(db).register(payload)
    return UserRead.model_validate(user)


@router.post(
    "/login", response_model=Token, summary="Obtain an access + refresh token pair"
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    _: Annotated[None, RateLimitedLogin],
) -> Token:
    service = AuthService(db)
    user = service.authenticate(form.username, form.password)
    return service.issue_token(user)


@router.post(
    "/refresh", response_model=Token, summary="Exchange a refresh token for a new pair"
)
def refresh(payload: RefreshRequest, db: DbSession) -> Token:
    return AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead, summary="Current authenticated user")
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)

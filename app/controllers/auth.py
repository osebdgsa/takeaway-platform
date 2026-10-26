"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.controllers.deps import CurrentUser, DbSession
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
)
def register(payload: UserCreate, db: DbSession) -> UserRead:
    user = AuthService(db).register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token, summary="Obtain a JWT access token")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    service = AuthService(db)
    user = service.authenticate(form.username, form.password)
    return service.issue_token(user)


@router.get("/me", response_model=UserRead, summary="Current authenticated user")
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)

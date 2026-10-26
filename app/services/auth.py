"""Registration, authentication and token issuing."""

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db) -> None:
        self.db = db
        self.users = UserRepository(db)

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
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value},
        )
        return Token(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

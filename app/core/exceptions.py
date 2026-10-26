"""Domain-level exceptions mapped to HTTP responses in one place."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for expected, domain-level failures."""

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(detail)


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class ValidationError(AppError):
    """Business-rule validation failure (distinct from Pydantic's 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    headers = {}
    if isinstance(exc, UnauthorizedError):
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )

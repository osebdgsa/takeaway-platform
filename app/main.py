"""FastAPI application factory and process entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.controllers.deps import DbSession
from app.controllers.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production and settings.SECRET_KEY == "dev-secret-change-me":
        raise RuntimeError("SECRET_KEY must be set in production")
    if settings.AUTO_CREATE_TABLES:
        logger.warning("AUTO_CREATE_TABLES is on; use Alembic outside local dev")
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=__version__,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": settings.PROJECT_NAME,
        "version": __version__,
        "docs": "/docs",
        "openapi": f"{settings.API_PREFIX}/openapi.json",
    }


@app.get("/health", tags=["health"])
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}

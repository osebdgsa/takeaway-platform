"""Application configuration loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Takeaway Platform API"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Auth
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg2://takeaway:takeaway@localhost:5432/takeaway"
    )
    SQL_ECHO: bool = False
    # Convenience for local development only; containers run Alembic instead.
    AUTO_CREATE_TABLES: bool = False

    # CORS: JSON array in env, e.g. CORS_ORIGINS=["https://example.com"]
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""
Preview Environment Platform - Application Configuration
=========================================================
Purpose:
  Centralizes settings parsed from environment variables injected by Kubernetes
  ConfigMaps, Secrets, or local .env files.
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from Environment Variables.
    """
    # Database connection string (PostgreSQL for preview/prod, SQLite for tests/local fallback)
    DATABASE_URL: str = "postgresql://preview_user:preview_password@postgres:5432/preview_db"

    # Ephemeral preview metadata injected via Kubernetes / CI
    APP_VERSION: str = "0.1.0"
    GIT_SHA: str = "development"
    PR_NUMBER: str = "local"

    # CORS Allowed Origins (can be comma-separated string or list)
    CORS_ORIGINS: Union[str, List[str]] = "*"

    # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL: str = "INFO"

    # Server Port
    PORT: int = 8000

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

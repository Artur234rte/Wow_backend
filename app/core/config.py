from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)

    app_name: str = Field("WoW Meta Aggregator API", validation_alias="APP_NAME")
    environment: Literal["local", "development", "production"] = Field(
        "local", validation_alias="ENVIRONMENT"
    )

    database_url: str = Field(
        "postgresql+asyncpg://wow:wowpass@postgres:5432/wowmeta", validation_alias="DATABASE_URL"
    )
    redis_url: str = Field("redis://redis:6379/0", validation_alias="REDIS_URL")

    wowlogs_client_id: str | None = Field(None, validation_alias="WOWLOGS_CLIENT_ID")
    wowlogs_client_secret: str | None = Field(None, validation_alias="WOWLOGS_CLIENT_SECRET")
    wowlogs_base_url: HttpUrl = Field("https://www.warcraftlogs.com", validation_alias="WOWLOGS_BASE_URL")
    wowlogs_api_path: str = Field("/api/v2/client", validation_alias="WOWLOGS_API_PATH")
    wowlogs_token_path: str = Field("/oauth/token", validation_alias="WOWLOGS_TOKEN_PATH")

    cache_ttl_seconds: int = Field(300, ge=30, validation_alias="CACHE_TTL_SECONDS")
    aggregation_schedule_hours: int = Field(8, ge=1, validation_alias="AGGREGATION_SCHEDULE_HOURS")
    current_patch: str = Field("latest", validation_alias="PATCH_VERSION")

    celery_broker_url: str = Field("redis://redis:6379/0", validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://redis:6379/1", validation_alias="CELERY_RESULT_BACKEND")

    request_timeout_seconds: float = Field(30.0, validation_alias="REQUEST_TIMEOUT_SECONDS")
    request_retries: int = Field(3, ge=0, le=10, validation_alias="REQUEST_RETRIES")
    request_retry_backoff: float = Field(1.5, ge=0.1, validation_alias="REQUEST_RETRY_BACKOFF")


@lru_cache
def get_settings() -> Settings:
    return Settings()

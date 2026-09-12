from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTOPS_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"
    max_batch_size: int = Field(default=1000, ge=1, le=10_000)
    retention_days: int = Field(default=30, ge=1, le=3650)
    capture_content: bool = False
    otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

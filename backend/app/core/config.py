from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql://mariam:mariam@localhost:5432/db_mariam"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "mariam-artifacts"
    api_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    mission_store: str = "memory"
    ai_resource_route_store: str = "memory"

    model_config = SettingsConfigDict(env_prefix="MARIAM_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

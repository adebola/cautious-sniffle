"""Configuration for the Workspace Service."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Workspace service settings."""

    service_name: str = "workspace-service"
    service_port: int = 8085

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chatcraft_workspace"

    # Pool settings
    db_pool_size: int = 20
    db_max_overflow: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()

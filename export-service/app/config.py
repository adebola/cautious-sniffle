"""Export Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Export Service settings."""

    service_name: str = "export-service"
    service_port: int = 8089


@lru_cache
def get_settings() -> Settings:
    return Settings()

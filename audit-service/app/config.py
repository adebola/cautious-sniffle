"""Audit Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Audit Service settings."""

    service_name: str = "audit-service"
    service_port: int = 8090

    # MongoDB
    mongodb_url: str = "mongodb://mongo:password@localhost:27017"
    mongodb_database: str = "chatcraft_audit"

    # Retention defaults (days) - can be overridden per org based on plan
    default_retention_days: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()

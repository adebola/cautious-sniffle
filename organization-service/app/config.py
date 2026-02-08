"""Configuration settings for the Organization Service."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Organization-service specific settings."""

    service_name: str = "organization-service"
    service_port: int = 8082

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/chatcraft_org"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Invitation settings
    invitation_expiry_hours: int = 72
    invitation_base_url: str = "http://localhost:3000/accept-invite"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()

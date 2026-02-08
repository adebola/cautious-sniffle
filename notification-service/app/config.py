"""Notification Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Notification Service settings."""

    service_name: str = "notification-service"
    service_port: int = 8088

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/chatcraft_notification"

    # Brevo (email)
    brevo_api_key: str = ""
    brevo_sender_email: str = "noreply@chatcraft.io"
    brevo_sender_name: str = "ChatCraft"
    brevo_api_url: str = "https://api.brevo.com/v3"

    # App URLs (for email links)
    app_base_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

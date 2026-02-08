"""Base settings class for all Python services."""

from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """Common settings shared by all Python services."""

    environment: str = "development"
    log_level: str = "DEBUG"
    redis_url: str = "redis://localhost:6379/0"

    # Internal service URLs
    auth_service_url: str = "http://localhost:8081"
    organization_service_url: str = "http://localhost:8082"
    document_service_url: str = "http://localhost:8083"
    workspace_service_url: str = "http://localhost:8085"
    billing_service_url: str = "http://localhost:8087"
    notification_service_url: str = "http://localhost:8088"
    audit_service_url: str = "http://localhost:8090"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

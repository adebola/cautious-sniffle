"""Document Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Document Service settings."""

    service_name: str = "document-service"
    service_port: int = 8083

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/chatcraft_doc"

    # MinIO / S3-compatible object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "chatcraft-documents"
    minio_secure: bool = False

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # Upload constraints
    max_file_size_mb: int = 50
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/csv",
    ]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

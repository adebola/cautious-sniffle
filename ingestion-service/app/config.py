"""Ingestion Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Ingestion Service settings."""

    service_name: str = "ingestion-service"
    service_port: int = 8084

    # MinIO / S3-compatible object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "chatcraft-documents"
    minio_secure: bool = False

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # OpenAI
    openai_api_key: str = ""

    # Embedding settings
    embedding_model: str = "text-embedding-3-small"

    # LLM for classification
    default_llm_model: str = "gpt-4o"

    # Chunking settings (in tokens)
    chunk_size: int = 512
    chunk_overlap: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()

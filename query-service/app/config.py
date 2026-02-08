"""Query Service configuration."""

from functools import lru_cache

from chatcraft_common.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Query Service settings."""

    service_name: str = "query-service"
    service_port: int = 8086

    # LLM API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Model defaults
    default_llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Token limits
    max_context_tokens: int = 8000
    max_response_tokens: int = 2000

    # Embedding dimensions (text-embedding-3-small = 1536)
    embedding_dimensions: int = 1536

    # Chunk search defaults
    default_chunk_limit: int = 15
    default_chunk_threshold: float = 0.3

    # Timeouts (seconds) for downstream service calls
    workspace_service_timeout: float = 10.0
    document_service_timeout: float = 15.0
    llm_timeout: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

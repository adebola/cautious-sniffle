"""Embedding generation via OpenAI API."""

import logging

from openai import AsyncOpenAI

from app.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings using the OpenAI Embeddings API."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a single embedding vector for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            openai.OpenAIError: If the API call fails.
        """
        # Truncate very long text to avoid token limits on the embedding model.
        # text-embedding-3-small supports up to 8191 tokens; a rough heuristic
        # is ~4 characters per token, so we cap at 30 000 characters.
        truncated = text[:30_000] if len(text) > 30_000 else text

        logger.debug("Generating embedding for text of length %d", len(truncated))

        response = await self._client.embeddings.create(
            input=truncated,
            model=self._model,
            dimensions=self._dimensions,
        )

        embedding = response.data[0].embedding
        logger.debug("Embedding generated: %d dimensions", len(embedding))
        return embedding

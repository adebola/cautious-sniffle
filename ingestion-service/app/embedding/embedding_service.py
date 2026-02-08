"""OpenAI embedding generation with batching and retry logic."""

import asyncio
import logging

from openai import AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)

# OpenAI allows up to 2048 inputs per embedding request
_MAX_BATCH_SIZE = 2048

# Exponential backoff settings
_MAX_RETRIES = 5
_BASE_DELAY_SECONDS = 1.0
_MAX_DELAY_SECONDS = 60.0


class EmbeddingService:
    """Generates vector embeddings using the OpenAI Embeddings API.

    Supports batching (up to 2048 texts per API call) and exponential backoff
    on rate-limit errors.
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text strings.

        Args:
            texts: The text strings to embed.

        Returns:
            A list of embedding vectors (each a list of floats), one per input text.
            The order matches the input order.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _MAX_BATCH_SIZE]
            batch_embeddings = await self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call the OpenAI API for a single batch with retry on rate-limit."""
        delay = _BASE_DELAY_SECONDS

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.embeddings.create(
                    input=texts,
                    model=self._model,
                )
                # The API returns embeddings sorted by index
                sorted_data = sorted(response.data, key=lambda d: d.index)
                return [item.embedding for item in sorted_data]

            except RateLimitError as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "Embedding rate limit exceeded after %d retries: %s",
                        _MAX_RETRIES,
                        exc,
                    )
                    raise
                logger.warning(
                    "Rate limited on embedding attempt %d/%d, retrying in %.1fs",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _MAX_DELAY_SECONDS)

            except Exception:
                logger.exception("Embedding API call failed on attempt %d", attempt)
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, _MAX_DELAY_SECONDS)

        # Should not reach here, but satisfy type checker
        raise RuntimeError("Embedding generation failed after all retries")

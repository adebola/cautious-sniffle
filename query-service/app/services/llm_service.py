"""LLM response generation supporting OpenAI and Anthropic models."""

import logging
from collections.abc import AsyncGenerator

import anthropic
from openai import AsyncOpenAI

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    """Generates responses from large language models.

    Supports OpenAI (gpt-*, o1-*) and Anthropic (claude-*) model families.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # ------------------------------------------------------------------
    # Provider detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_openai_model(model: str) -> bool:
        return model.startswith("gpt") or model.startswith("o1")

    @staticmethod
    def _is_anthropic_model(model: str) -> bool:
        return model.startswith("claude")

    def _resolve_model(self, model: str | None) -> str:
        return model or self._settings.default_llm_model

    # ------------------------------------------------------------------
    # Non-streaming
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> dict:
        """Generate a complete (non-streaming) LLM response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model identifier. Falls back to default_llm_model from settings.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            A dict with keys: content (str), model (str), input_tokens (int),
            output_tokens (int).
        """
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self._settings.max_response_tokens

        if self._is_openai_model(resolved_model):
            return await self._openai_generate(messages, resolved_model, temperature, max_tok)
        elif self._is_anthropic_model(resolved_model):
            return await self._anthropic_generate(messages, resolved_model, temperature, max_tok)
        else:
            # Default to OpenAI for unrecognised prefixes
            logger.warning("Unrecognised model prefix '%s', falling back to OpenAI", resolved_model)
            return await self._openai_generate(messages, resolved_model, temperature, max_tok)

    async def _openai_generate(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        logger.info("OpenAI non-streaming request: model=%s", model)

        response = await self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        return {
            "content": choice.message.content or "",
            "model": response.model,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }

    async def _anthropic_generate(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        logger.info("Anthropic non-streaming request: model=%s", model)

        # Anthropic expects `system` separately and messages without a system role.
        system_prompt, filtered_messages = self._extract_system_for_anthropic(messages)

        response = await self._anthropic_client.messages.create(
            model=model,
            system=system_prompt,
            messages=filtered_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return {
            "content": content,
            "model": response.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream_response(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM tokens as an async generator.

        Yields individual string tokens as they are produced.
        """
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self._settings.max_response_tokens

        if self._is_openai_model(resolved_model):
            async for token in self._openai_stream(messages, resolved_model, temperature, max_tok):
                yield token
        elif self._is_anthropic_model(resolved_model):
            async for token in self._anthropic_stream(messages, resolved_model, temperature, max_tok):
                yield token
        else:
            logger.warning("Unrecognised model prefix '%s', falling back to OpenAI streaming", resolved_model)
            async for token in self._openai_stream(messages, resolved_model, temperature, max_tok):
                yield token

    async def _openai_stream(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        logger.info("OpenAI streaming request: model=%s", model)

        stream = await self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _anthropic_stream(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        logger.info("Anthropic streaming request: model=%s", model)

        system_prompt, filtered_messages = self._extract_system_for_anthropic(messages)

        async with self._anthropic_client.messages.stream(
            model=model,
            system=system_prompt,
            messages=filtered_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_system_for_anthropic(
        messages: list[dict],
    ) -> tuple[str, list[dict]]:
        """Separate the system prompt from conversation messages.

        Anthropic's API requires the system prompt as a dedicated parameter
        rather than as a message with role='system'.
        """
        system_prompt = ""
        filtered: list[dict] = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered.append({"role": msg["role"], "content": msg["content"]})

        return system_prompt, filtered

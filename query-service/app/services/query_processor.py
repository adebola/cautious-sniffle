"""Core query processing pipeline -- the heart of the Query Service.

Orchestrates workspace access checks, chunk retrieval, LLM generation,
citation extraction, and message persistence.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from uuid import UUID

import httpx
import tiktoken

from chatcraft_common.clients import ServiceClient
from chatcraft_common.errors import (
    ChatCraftException,
    ErrorCode,
    ForbiddenException,
    NotFoundException,
)

from app.config import Settings
from app.services.citation_extractor import extract_citations
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class QueryProcessor:
    """End-to-end RAG query processor.

    This class coordinates the full pipeline:
    1. Verify workspace access
    2. Retrieve workspace details (system prompt, settings)
    3. Retrieve session details (selected document IDs, history)
    4. Generate embedding for the user question
    5. Search for relevant chunks via the Document Service
    6. Build the LLM prompt with context, history, and sources
    7. Generate the answer (streaming or non-streaming)
    8. Extract citations
    9. Persist messages via the Workspace Service
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._workspace_client = ServiceClient(
            base_url=settings.workspace_service_url,
            timeout=settings.workspace_service_timeout,
        )
        self._document_client = ServiceClient(
            base_url=settings.document_service_url,
            timeout=settings.document_service_timeout,
        )
        self._embedding_service = EmbeddingService(settings)
        self._llm_service = LLMService(settings)

        # tiktoken encoder for token counting (cl100k_base covers GPT-4 family)
        try:
            self._encoder = tiktoken.encoding_for_model(settings.default_llm_model)
        except KeyError:
            self._encoder = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process_query(
        self,
        user_id: UUID,
        org_id: UUID,
        workspace_id: UUID,
        session_id: UUID,
        question: str,
        stream: bool = False,
        model: str | None = None,
    ):
        """Process a user query against a workspace.

        For non-streaming: returns a dict matching ``QueryResponse``.
        For streaming: returns an ``AsyncGenerator`` that yields SSE-ready dicts.
        """
        start_time = time.monotonic()

        # 1. Verify workspace access
        await self._verify_access(workspace_id, user_id)

        # 2. Get workspace details
        workspace = await self._get_workspace(workspace_id)

        # 3. Get session details (includes message history)
        session = await self._get_session(session_id)
        selected_doc_ids = session.get("selected_document_ids", [])

        if not selected_doc_ids:
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.QUERY_NO_DOCUMENTS,
                message="No documents selected in this session. Please select at least one document.",
            )

        # 4. Generate embedding for the question
        query_embedding = await self._embedding_service.generate_embedding(question)

        # 5. Search chunks
        sources = await self._search_chunks(query_embedding, selected_doc_ids)

        if not sources:
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.QUERY_NO_DOCUMENTS,
                message="No relevant content found in the selected documents for this query.",
            )

        # 6. Build LLM messages
        resolved_model = model or self._settings.default_llm_model
        messages = self._build_messages(workspace, session, sources, question)

        if stream:
            return self._stream_pipeline(
                messages=messages,
                sources=sources,
                model=resolved_model,
                user_id=user_id,
                session_id=session_id,
                question=question,
                start_time=start_time,
            )

        # 7. Non-streaming: generate full response
        llm_result = await self._llm_service.generate_response(
            messages=messages,
            model=resolved_model,
        )

        answer = llm_result["content"]

        # 8. Extract citations
        citations = extract_citations(answer, sources)

        # 9. Store messages
        await self._store_messages(
            session_id=session_id,
            user_id=user_id,
            question=question,
            answer=answer,
            citations=citations,
            model=llm_result["model"],
        )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "answer": answer,
            "citations": citations,
            "model_used": llm_result["model"],
            "token_usage": {
                "input": llm_result["input_tokens"],
                "output": llm_result["output_tokens"],
            },
            "latency_ms": elapsed_ms,
        }

    # ------------------------------------------------------------------
    # Streaming pipeline
    # ------------------------------------------------------------------

    async def _stream_pipeline(
        self,
        messages: list[dict],
        sources: list[dict],
        model: str,
        user_id: UUID,
        session_id: UUID,
        question: str,
        start_time: float,
    ) -> AsyncGenerator[dict, None]:
        """Yield SSE-compatible event dicts while streaming LLM output."""
        full_response = ""

        try:
            async for token in self._llm_service.stream_response(
                messages=messages,
                model=model,
            ):
                full_response += token
                yield {"event": "token", "data": token}

            # After streaming completes, extract citations from the full response
            citations = extract_citations(full_response, sources)

            # Store messages (fire-and-forget style, but we await to ensure delivery)
            await self._store_messages(
                session_id=session_id,
                user_id=user_id,
                question=question,
                answer=full_response,
                citations=citations,
                model=model,
            )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Yield citations event
            yield {
                "event": "citations",
                "data": json.dumps(
                    {"citations": citations, "latency_ms": elapsed_ms},
                    default=str,
                ),
            }

            # Yield done event
            yield {"event": "done", "data": ""}

        except Exception as exc:
            logger.exception("Error during streaming pipeline")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    # ------------------------------------------------------------------
    # Workspace / session access
    # ------------------------------------------------------------------

    async def _verify_access(self, workspace_id: UUID, user_id: UUID) -> None:
        """Verify the user has access to the workspace."""
        try:
            result = await self._workspace_client.get(
                f"/internal/workspaces/{workspace_id}/access-check",
                params={"user_id": str(user_id)},
            )
            if not result.get("data", {}).get("has_access", False):
                raise ForbiddenException("You do not have access to this workspace")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise ForbiddenException("You do not have access to this workspace")
            if exc.response.status_code == 404:
                raise NotFoundException(ErrorCode.WS_NOT_FOUND, "Workspace not found")
            raise ChatCraftException(
                status_code=502,
                code=ErrorCode.QUERY_LLM_ERROR,
                message=f"Failed to verify workspace access: {exc}",
            )

    async def _get_workspace(self, workspace_id: UUID) -> dict:
        """Retrieve workspace details (system prompt, settings)."""
        try:
            result = await self._workspace_client.get(
                f"/internal/workspaces/{workspace_id}",
            )
            return result.get("data", {})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(ErrorCode.WS_NOT_FOUND, "Workspace not found")
            raise ChatCraftException(
                status_code=502,
                code=ErrorCode.QUERY_LLM_ERROR,
                message=f"Failed to retrieve workspace details: {exc}",
            )

    async def _get_session(self, session_id: UUID) -> dict:
        """Retrieve session details including selected_document_ids and message history."""
        try:
            result = await self._workspace_client.get(
                f"/internal/workspaces/sessions/{session_id}",
            )
            return result.get("data", {})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(ErrorCode.WS_NOT_FOUND, "Session not found")
            raise ChatCraftException(
                status_code=502,
                code=ErrorCode.QUERY_LLM_ERROR,
                message=f"Failed to retrieve session: {exc}",
            )

    # ------------------------------------------------------------------
    # Document / chunk search
    # ------------------------------------------------------------------

    async def _search_chunks(
        self,
        query_embedding: list[float],
        document_ids: list[str],
    ) -> list[dict]:
        """Search for relevant chunks via the Document Service."""
        try:
            # Convert string UUIDs to proper format for the request body
            doc_ids = [str(did) for did in document_ids]

            result = await self._document_client.post(
                "/internal/documents/chunks/search",
                json={
                    "query_embedding": query_embedding,
                    "document_ids": doc_ids,
                    "limit": self._settings.default_chunk_limit,
                    "threshold": self._settings.default_chunk_threshold,
                },
            )

            raw_results = result.get("data", [])
            return self._format_search_results(raw_results)

        except httpx.HTTPStatusError as exc:
            logger.error("Chunk search failed: %s", exc)
            raise ChatCraftException(
                status_code=502,
                code=ErrorCode.QUERY_LLM_ERROR,
                message=f"Failed to search document chunks: {exc}",
            )

    @staticmethod
    def _format_search_results(raw_results: list[dict]) -> list[dict]:
        """Normalise the chunk search results into a consistent internal format.

        The Document Service returns objects shaped like ``ChunkSearchResult``:
        ``{ chunk: {...}, similarity: float, document_title, document_filename }``
        """
        formatted: list[dict] = []
        for item in raw_results:
            chunk = item.get("chunk", {})
            formatted.append({
                "chunk_id": chunk.get("id", ""),
                "document_id": chunk.get("document_id", ""),
                "document_name": item.get("document_title") or item.get("document_filename", "Unknown"),
                "content": chunk.get("content", ""),
                "page_number": chunk.get("page_number"),
                "section": chunk.get("section_title"),
                "similarity": item.get("similarity", 0.0),
            })
        return formatted

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        workspace: dict,
        session: dict,
        sources: list[dict],
        question: str,
    ) -> list[dict]:
        """Assemble the messages array for the LLM call.

        Structure:
        1. System message (workspace template + source references)
        2. Conversation history (previous messages in the session)
        3. Current user question
        """
        messages: list[dict] = []

        # -- System prompt ------------------------------------------------
        system_prompt = self._build_system_prompt(workspace, sources)
        messages.append({"role": "system", "content": system_prompt})

        # -- Conversation history -----------------------------------------
        history = session.get("messages", [])
        token_budget = self._settings.max_context_tokens
        history_tokens = 0

        # Walk history in reverse so we include the most recent messages
        trimmed_history: list[dict] = []
        for msg in reversed(history):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            msg_tokens = len(self._encoder.encode(content))

            if history_tokens + msg_tokens > token_budget:
                break
            history_tokens += msg_tokens
            trimmed_history.append({"role": role, "content": content})

        # Restore chronological order
        trimmed_history.reverse()
        messages.extend(trimmed_history)

        # -- Current question ---------------------------------------------
        messages.append({"role": "user", "content": question})

        return messages

    def _build_system_prompt(self, workspace: dict, sources: list[dict]) -> str:
        """Construct the system prompt with workspace instructions and source references."""
        parts: list[str] = []

        # Workspace-level system prompt / template
        ws_prompt = workspace.get("system_prompt") or workspace.get("prompt_template", "")
        if ws_prompt:
            parts.append(ws_prompt)
        else:
            parts.append(
                "You are a helpful AI assistant. Answer questions based on the provided "
                "source documents. Always cite your sources using [N] markers that correspond "
                "to the numbered references below."
            )

        # Citation instructions
        parts.append(
            "\n\nIMPORTANT: When referencing information from the sources below, "
            "cite them using [N] notation where N is the source number. "
            "If the sources do not contain enough information to answer the question, "
            "say so clearly rather than making up information."
        )

        # Formatted sources
        parts.append("\n\n--- SOURCES ---\n")
        for i, source in enumerate(sources, start=1):
            doc_name = source.get("document_name", "Unknown")
            page = source.get("page_number")
            section = source.get("section")
            content = source.get("content", "")

            header = f"[{i}] Document: {doc_name}"
            if page is not None:
                header += f", Page {page}"
            if section:
                header += f", Section: {section}"
            header += "\n"

            # Truncate very long chunks to fit context budget
            truncated_content = content[:2000] if len(content) > 2000 else content
            parts.append(f"{header}{truncated_content}\n")

        parts.append("--- END SOURCES ---")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Message persistence
    # ------------------------------------------------------------------

    async def _store_messages(
        self,
        session_id: UUID,
        user_id: UUID,
        question: str,
        answer: str,
        citations: list[dict],
        model: str,
    ) -> None:
        """Persist both the user message and assistant message via the Workspace Service."""
        try:
            await self._workspace_client.post(
                f"/internal/workspaces/sessions/{session_id}/messages",
                json={
                    "messages": [
                        {
                            "id": str(uuid.uuid4()),
                            "role": "user",
                            "content": question,
                            "user_id": str(user_id),
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "role": "assistant",
                            "content": answer,
                            "citations": citations,
                            "model": model,
                        },
                    ],
                },
            )
            logger.info("Stored user and assistant messages for session %s", session_id)
        except httpx.HTTPStatusError as exc:
            # Log but do not fail the query if message storage fails
            logger.error(
                "Failed to store messages for session %s: %s",
                session_id,
                exc,
            )

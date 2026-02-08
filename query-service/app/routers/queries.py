"""Query router -- handles user questions against workspace documents."""

import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from chatcraft_common.auth import CurrentUser
from chatcraft_common.errors import ChatCraftException

from app.dependencies import get_current_user, get_query_processor
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_processor import QueryProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["query"])


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Submit a query",
    description=(
        "Process a user question against a workspace's selected documents. "
        "Set `stream=true` in the request body to receive the response as "
        "Server-Sent Events."
    ),
)
async def process_query(
    body: QueryRequest,
    user: CurrentUser = Depends(get_current_user),
    processor: QueryProcessor = Depends(get_query_processor),
):
    """Process a query, returning either a full JSON response or an SSE stream."""
    try:
        if body.stream:
            return await _handle_stream(body, user, processor)

        result = await processor.process_query(
            user_id=user.user_id,
            org_id=user.organization_id,
            workspace_id=body.workspace_id,
            session_id=body.session_id,
            question=body.question,
            stream=False,
            model=body.model,
        )
        return QueryResponse(**result)

    except ChatCraftException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error processing query")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/stream",
    summary="Submit a streaming query",
    description=(
        "Convenience endpoint that always returns an SSE stream. "
        "Equivalent to calling POST / with stream=true."
    ),
)
async def process_query_stream(
    body: QueryRequest,
    user: CurrentUser = Depends(get_current_user),
    processor: QueryProcessor = Depends(get_query_processor),
):
    """Always-streaming variant of the query endpoint."""
    try:
        return await _handle_stream(body, user, processor)
    except ChatCraftException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error processing streaming query")
        raise HTTPException(status_code=500, detail=str(exc))


async def _handle_stream(
    body: QueryRequest,
    user: CurrentUser,
    processor: QueryProcessor,
) -> EventSourceResponse:
    """Set up and return an SSE EventSourceResponse for a streaming query."""
    # process_query with stream=True returns an async generator
    event_generator: AsyncGenerator[dict, None] = await processor.process_query(
        user_id=user.user_id,
        org_id=user.organization_id,
        workspace_id=body.workspace_id,
        session_id=body.session_id,
        question=body.question,
        stream=True,
        model=body.model,
    )

    async def sse_generator():
        """Adapt the QueryProcessor event stream into SSE-compatible dicts."""
        async for event in event_generator:
            yield {
                "event": event["event"],
                "data": event["data"],
            }

    return EventSourceResponse(sse_generator())

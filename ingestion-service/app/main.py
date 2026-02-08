"""Ingestion Service - FastAPI application.

Serves health and status endpoints and starts the RabbitMQ background worker
on application startup.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from chatcraft_common.clients import ServiceClient
from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.worker import start_worker

logger = logging.getLogger(__name__)

settings = get_settings()

# Hold a reference to the background worker task so it is not garbage-collected
_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start RabbitMQ worker on startup, cancel on shutdown."""
    global _worker_task

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.DEBUG),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "Starting Ingestion Service (port %d, env %s)",
        settings.service_port,
        settings.environment,
    )

    # Launch the RabbitMQ consumer as a background task
    _worker_task = asyncio.create_task(_run_worker_with_retry())

    yield

    # Shutdown
    logger.info("Shutting down Ingestion Service")
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass


async def _run_worker_with_retry() -> None:
    """Wrapper that restarts the worker on connection errors with backoff."""
    delay = 1.0
    max_delay = 30.0

    while True:
        try:
            await start_worker(settings)
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")
            raise
        except Exception:
            logger.exception(
                "RabbitMQ worker died, restarting in %.1fs",
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


app = FastAPI(
    title="ChatCraft Ingestion Service",
    description="Processes uploaded documents: parsing, chunking, embedding, and classification.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
app.include_router(health_router)


# ---------------------------------------------------------------------------
# Status endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/ingestion/status/{document_id}", tags=["ingestion"])
async def get_document_status(document_id: str):
    """Proxy the document processing status from the Document Service.

    This is a convenience endpoint so callers do not need to know the
    Document Service URL.
    """
    doc_client = ServiceClient(
        base_url=settings.document_service_url,
        timeout=10.0,
    )
    try:
        result = await doc_client.get(f"/internal/documents/{document_id}/status")
        return result
    except Exception as exc:
        logger.error("Failed to fetch status for document %s: %s", document_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve document status: {exc}",
        )


@app.get("/api/v1/ingestion/info", tags=["ingestion"])
async def ingestion_info():
    """Return basic configuration metadata about the ingestion service."""
    return {
        "service": settings.service_name,
        "embedding_model": settings.embedding_model,
        "classification_model": settings.default_llm_model,
        "chunk_size_tokens": settings.chunk_size,
        "chunk_overlap_tokens": settings.chunk_overlap,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
    )

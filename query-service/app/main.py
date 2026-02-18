"""Query Service - FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.routers import queries
from app.services.query_processor import QueryProcessor

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.DEBUG),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )

    # Create the query processor (holds service clients and LLM clients)
    query_processor = QueryProcessor(settings)
    app.state.query_processor = query_processor

    logger.info(
        "Query Service started on port %s (env=%s, model=%s)",
        settings.service_port,
        settings.environment,
        settings.default_llm_model,
    )
    yield

    # Shutdown
    logger.info("Query Service shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatCraft Query Service",
        description=(
            "Orchestrates RAG queries: embeds user questions, retrieves relevant "
            "document chunks, generates LLM answers with citations, and persists "
            "conversation history."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(health_router)
    app.include_router(queries.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )

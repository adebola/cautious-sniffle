"""Document Service - FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatcraft_common.database import create_db_engine, create_session_factory
from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.routers import documents, internal
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()

    # Database
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Object storage
    storage_service = StorageService(settings)
    try:
        await storage_service.ensure_bucket()
    except Exception:
        logger.warning("Could not connect to MinIO on startup - bucket creation deferred")

    # Application services
    document_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    document_service = DocumentService(
        settings=settings,
        storage_service=storage_service,
        document_repo=document_repo,
        chunk_repo=chunk_repo,
    )
    app.state.document_service = document_service

    logger.info("Document Service started on port %s", settings.service_port)
    yield

    # Shutdown
    await engine.dispose()
    logger.info("Document Service shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatCraft Document Service",
        description="Manages document upload, storage, and vector search for ChatCraft Professional.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(health_router)
    app.include_router(documents.router)
    app.include_router(internal.router)

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

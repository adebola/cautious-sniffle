"""Audit Service - FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.database import create_indexes, create_motor_client, get_database
from app.routers import audit, internal
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()

    # MongoDB client
    client = create_motor_client(settings)
    database = get_database(client, settings)

    # Create indexes (idempotent)
    await create_indexes(database)

    # Service layer
    audit_service = AuditService(
        database=database,
        default_retention_days=settings.default_retention_days,
    )

    # Store on app state for dependency injection
    app.state.motor_client = client
    app.state.database = database
    app.state.audit_service = audit_service

    logger.info("Audit Service started on port %s", settings.service_port)
    yield

    # Shutdown
    client.close()
    logger.info("Audit Service shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatCraft Audit Service",
        description="Centralized audit trail for all ChatCraft Professional services.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(health_router)
    app.include_router(audit.router)
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

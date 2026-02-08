"""Export Service - FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chatcraft_common.health import router as health_router

from app.clients.audit_client import AuditClient
from app.clients.workspace_client import WorkspaceClient
from app.config import get_settings
from app.routers import exports
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()

    # Internal-API clients
    workspace_client = WorkspaceClient(base_url=settings.workspace_service_url)
    audit_client = AuditClient(base_url=settings.audit_service_url)

    # Application service
    export_service = ExportService(
        workspace_client=workspace_client,
        audit_client=audit_client,
    )

    app.state.export_service = export_service

    logger.info("Export Service started on port %s", settings.service_port)
    yield

    logger.info("Export Service shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatCraft Export Service",
        description="Exports query sessions (DOCX/PDF/Markdown) and audit logs (CSV/XLSX) for ChatCraft Professional.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(exports.router)

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

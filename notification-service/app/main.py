"""Notification Service - FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatcraft_common.database import create_db_engine, create_session_factory
from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.repositories.notification_repository import NotificationRepository
from app.routers import internal, notifications
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

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

    # Repositories
    notification_repo = NotificationRepository()

    # Services
    notification_service = NotificationService(notification_repo=notification_repo)
    email_service = EmailService(settings=settings)

    app.state.notification_service = notification_service
    app.state.email_service = email_service

    logger.info("Notification Service started on port %s", settings.service_port)
    yield

    # Shutdown
    await engine.dispose()
    logger.info("Notification Service shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatCraft Notification Service",
        description="Manages in-app notifications and email delivery for ChatCraft Professional.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Routers
    app.include_router(health_router)
    app.include_router(notifications.router)
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

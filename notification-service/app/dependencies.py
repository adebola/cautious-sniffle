"""FastAPI dependency injection wiring for the Notification Service."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, get_current_user  # noqa: F401

from app.services.email_service import EmailService
from app.services.notification_service import NotificationService


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session from the application-level factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_notification_service(request: Request) -> NotificationService:
    """Return the application-scoped NotificationService singleton."""
    return request.app.state.notification_service


def get_email_service(request: Request) -> EmailService:
    """Return the application-scoped EmailService singleton."""
    return request.app.state.email_service


# Re-export for convenient router imports
__all__ = [
    "get_session",
    "get_notification_service",
    "get_email_service",
    "get_current_user",
    "CurrentUser",
]

"""FastAPI dependency injection wiring for the Document Service."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, get_current_user  # noqa: F401

from app.services.document_service import DocumentService


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


def get_document_service(request: Request) -> DocumentService:
    """Return the application-scoped DocumentService singleton."""
    return request.app.state.document_service


# Re-export for convenient router imports
__all__ = [
    "get_session",
    "get_document_service",
    "get_current_user",
    "CurrentUser",
]

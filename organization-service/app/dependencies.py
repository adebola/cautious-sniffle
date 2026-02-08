"""Shared FastAPI dependencies for the Organization Service."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser
from chatcraft_common.auth import get_current_user as _get_current_user

from app.config import Settings, get_settings as _get_settings


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session from the application session factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    user: CurrentUser = Depends(_get_current_user),
) -> CurrentUser:
    """Re-export get_current_user from chatcraft_common.auth."""
    return user


def get_settings() -> Settings:
    """Return the Settings singleton."""
    return _get_settings()

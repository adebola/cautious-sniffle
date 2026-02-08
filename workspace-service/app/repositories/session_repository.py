"""Session repository for database operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.models.session import QuerySession


class SessionRepository:
    """Data access layer for query sessions."""

    async def create(
        self, session: AsyncSession, query_session: QuerySession
    ) -> QuerySession:
        session.add(query_session)
        await session.flush()
        return query_session

    async def get_by_id(
        self, session: AsyncSession, session_id: uuid.UUID
    ) -> QuerySession | None:
        result = await session.execute(
            select(QuerySession).where(QuerySession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_messages(
        self, session: AsyncSession, session_id: uuid.UUID
    ) -> QuerySession | None:
        result = await session.execute(
            select(QuerySession)
            .options(selectinload(QuerySession.messages))
            .where(QuerySession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[QuerySession]:
        result = await session.execute(
            select(QuerySession)
            .where(QuerySession.workspace_id == workspace_id)
            .order_by(QuerySession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(
        self, session: AsyncSession, message: Message
    ) -> Message:
        session.add(message)
        await session.flush()
        return message

    async def list_messages(
        self, session: AsyncSession, session_id: uuid.UUID
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

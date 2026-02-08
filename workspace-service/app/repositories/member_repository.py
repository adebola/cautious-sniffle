"""Member repository for database operations."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import WorkspaceMember


class MemberRepository:
    """Data access layer for workspace members."""

    async def create(
        self, session: AsyncSession, member: WorkspaceMember
    ) -> WorkspaceMember:
        session.add(member)
        await session.flush()
        return member

    async def get_by_workspace_and_user(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceMember | None:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        result = await session.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.added_at.asc())
        )
        return list(result.scalars().all())

    async def update_role(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMember | None:
        await session.execute(
            update(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .values(role=new_role)
        )
        await session.flush()
        return await self.get_by_workspace_and_user(session, workspace_id, user_id)

    async def delete(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        member = await self.get_by_workspace_and_user(session, workspace_id, user_id)
        if member:
            await session.delete(member)
            await session.flush()
            return True
        return False

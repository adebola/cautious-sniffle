"""Workspace repository for database operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import WorkspaceDocument
from app.models.member import WorkspaceMember
from app.models.session import QuerySession
from app.models.workspace import Workspace


class WorkspaceRepository:
    """Data access layer for workspaces."""

    async def create(self, session: AsyncSession, workspace: Workspace) -> Workspace:
        session.add(workspace)
        await session.flush()
        # Reload with template relationship
        result = await session.execute(
            select(Workspace)
            .options(selectinload(Workspace.template))
            .where(Workspace.id == workspace.id)
        )
        return result.scalar_one()

    async def get_by_id(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> Workspace | None:
        result = await session.execute(
            select(Workspace)
            .options(selectinload(Workspace.template))
            .where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user_membership(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Workspace], int]:
        """List workspaces where the user is a member within the organization."""
        base_query = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .options(selectinload(Workspace.template))
            .where(
                Workspace.organization_id == organization_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if status:
            base_query = base_query.where(Workspace.status == status)

        # Count query
        count_query = (
            select(func.count())
            .select_from(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.organization_id == organization_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if status:
            count_query = count_query.where(Workspace.status == status)

        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        items_query = base_query.order_by(Workspace.updated_at.desc()).offset(offset).limit(limit)
        items_result = await session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def update_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        **kwargs,
    ) -> Workspace | None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await session.execute(
            update(Workspace).where(Workspace.id == workspace_id).values(**kwargs)
        )
        await session.flush()
        return await self.get_by_id(session, workspace_id)

    async def get_document_count(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> int:
        result = await session.execute(
            select(func.count()).where(WorkspaceDocument.workspace_id == workspace_id)
        )
        return result.scalar() or 0

    async def get_member_count(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> int:
        result = await session.execute(
            select(func.count()).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return result.scalar() or 0

    async def get_session_count(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> int:
        result = await session.execute(
            select(func.count()).where(QuerySession.workspace_id == workspace_id)
        )
        return result.scalar() or 0

    async def add_document(
        self, session: AsyncSession, doc: WorkspaceDocument
    ) -> WorkspaceDocument:
        session.add(doc)
        await session.flush()
        return doc

    async def get_document(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> WorkspaceDocument | None:
        result = await session.execute(
            select(WorkspaceDocument).where(
                WorkspaceDocument.workspace_id == workspace_id,
                WorkspaceDocument.document_id == document_id,
            )
        )
        return result.scalar_one_or_none()

    async def remove_document(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> bool:
        doc = await self.get_document(session, workspace_id, document_id)
        if doc:
            await session.delete(doc)
            await session.flush()
            return True
        return False

    async def list_documents(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> list[WorkspaceDocument]:
        result = await session.execute(
            select(WorkspaceDocument)
            .where(WorkspaceDocument.workspace_id == workspace_id)
            .order_by(WorkspaceDocument.added_at.desc())
        )
        return list(result.scalars().all())

    async def get_document_ids(
        self, session: AsyncSession, workspace_id: uuid.UUID
    ) -> list[uuid.UUID]:
        result = await session.execute(
            select(WorkspaceDocument.document_id).where(
                WorkspaceDocument.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())

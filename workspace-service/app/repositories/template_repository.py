"""Template repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import WorkspaceTemplate


class TemplateRepository:
    """Data access layer for workspace templates."""

    async def list_active(
        self, session: AsyncSession
    ) -> list[WorkspaceTemplate]:
        result = await session.execute(
            select(WorkspaceTemplate)
            .where(WorkspaceTemplate.is_active.is_(True))
            .order_by(WorkspaceTemplate.display_order.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, session: AsyncSession, template_id: str
    ) -> WorkspaceTemplate | None:
        result = await session.execute(
            select(WorkspaceTemplate).where(WorkspaceTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

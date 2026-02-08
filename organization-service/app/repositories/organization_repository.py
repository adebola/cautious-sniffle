"""Repository for organization_settings table operations."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationSettings


class OrganizationSettingsRepository:
    """Async CRUD operations for the organization_settings table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_org_id(self, organization_id: UUID) -> OrganizationSettings | None:
        """Return settings for the given organization, or None."""
        stmt = select(OrganizationSettings).where(
            OrganizationSettings.organization_id == organization_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        organization_id: UUID,
        *,
        timezone_val: str | None = None,
        default_workspace_template: str | None = None,
        allowed_templates: list[str] | None = None,
        features: dict[str, Any] | None = None,
    ) -> OrganizationSettings:
        """Insert or update organization settings (PostgreSQL upsert)."""
        now = datetime.now(timezone.utc)

        insert_values: dict[str, Any] = {
            "organization_id": organization_id,
            "created_at": now,
            "updated_at": now,
        }
        update_values: dict[str, Any] = {"updated_at": now}

        if timezone_val is not None:
            insert_values["timezone"] = timezone_val
            update_values["timezone"] = timezone_val
        if default_workspace_template is not None:
            insert_values["default_workspace_template"] = default_workspace_template
            update_values["default_workspace_template"] = default_workspace_template
        if allowed_templates is not None:
            insert_values["allowed_templates"] = allowed_templates
            update_values["allowed_templates"] = allowed_templates
        if features is not None:
            insert_values["features"] = features
            update_values["features"] = features

        stmt = (
            pg_insert(OrganizationSettings)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["organization_id"],
                set_=update_values,
            )
            .returning(OrganizationSettings)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_org_id(self, organization_id: UUID) -> bool:
        """Delete settings for an organization. Returns True if a row was deleted."""
        settings = await self.get_by_org_id(organization_id)
        if settings is None:
            return False
        await self._session.delete(settings)
        return True

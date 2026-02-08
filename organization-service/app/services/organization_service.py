"""Service for organization-level operations.

Core org data lives in the auth service. This service proxies reads/writes
via internal HTTP calls and enriches responses with locally-stored settings
and cross-service usage data.
"""

import logging
from typing import Any
from uuid import UUID

import httpx

from chatcraft_common.clients import ServiceClient
from chatcraft_common.errors import ErrorCode, NotFoundException

from app.config import Settings
from app.repositories.organization_repository import OrganizationSettingsRepository
from app.schemas.organization import OrganizationResponse, OrganizationUpdate, OrganizationUsage

logger = logging.getLogger(__name__)


class OrganizationService:
    """High-level organization operations."""

    def __init__(
        self,
        settings: Settings,
        org_settings_repo: OrganizationSettingsRepository | None = None,
    ) -> None:
        self._auth_client = ServiceClient(settings.auth_service_url)
        self._doc_client = ServiceClient(settings.document_service_url)
        self._workspace_client = ServiceClient(settings.workspace_service_url)
        self._billing_client = ServiceClient(settings.billing_service_url)
        self._org_settings_repo = org_settings_repo

    async def get_current_organization(self, org_id: UUID) -> OrganizationResponse:
        """Fetch organization details from the auth service's internal API."""
        try:
            response = await self._auth_client.get(
                f"/internal/organizations/{org_id}"
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_NOT_FOUND,
                    message=f"Organization {org_id} not found",
                )
            raise

        org_data: dict[str, Any] = response.get("data", response)

        # Enrich with locally-stored extended settings if available
        if self._org_settings_repo is not None:
            local_settings = await self._org_settings_repo.get_by_org_id(org_id)
            if local_settings is not None:
                org_data.setdefault("settings", {}).update(
                    {
                        "timezone": local_settings.timezone,
                        "default_workspace_template": local_settings.default_workspace_template,
                        "allowed_templates": local_settings.allowed_templates or [],
                        "features": local_settings.features or {},
                    }
                )

        return OrganizationResponse(**org_data)

    async def update_organization(
        self,
        org_id: UUID,
        update_data: OrganizationUpdate,
    ) -> OrganizationResponse:
        """Update organization details via the auth service's internal API."""
        payload = update_data.model_dump(exclude_none=True)
        if not payload:
            # Nothing to update -- return current state
            return await self.get_current_organization(org_id)

        try:
            response = await self._auth_client.put(
                f"/internal/organizations/{org_id}",
                json=payload,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_NOT_FOUND,
                    message=f"Organization {org_id} not found",
                )
            raise

        org_data: dict[str, Any] = response.get("data", response)
        return OrganizationResponse(**org_data)

    async def get_organization_usage(self, org_id: UUID) -> OrganizationUsage:
        """Aggregate usage statistics from multiple downstream services.

        TODO: Replace mock data with real inter-service calls once the
        document, workspace, and billing services expose usage endpoints.
        """
        workspace_count = 0
        document_count = 0
        member_count = 0
        storage_bytes = 0

        # -- workspace count ---------------------------------------------------
        try:
            ws_resp = await self._workspace_client.get(
                f"/internal/organizations/{org_id}/usage"
            )
            workspace_count = ws_resp.get("data", {}).get("workspace_count", 0)
        except Exception:
            logger.warning("Failed to fetch workspace usage for org %s", org_id)

        # -- document count & storage ------------------------------------------
        try:
            doc_resp = await self._doc_client.get(
                f"/internal/organizations/{org_id}/usage"
            )
            doc_data = doc_resp.get("data", {})
            document_count = doc_data.get("document_count", 0)
            storage_bytes = doc_data.get("storage_bytes", 0)
        except Exception:
            logger.warning("Failed to fetch document usage for org %s", org_id)

        # -- member count (from auth service) ----------------------------------
        try:
            auth_resp = await self._auth_client.get(
                f"/internal/organizations/{org_id}/users/count"
            )
            member_count = auth_resp.get("data", {}).get("count", 0)
        except Exception:
            logger.warning("Failed to fetch member count for org %s", org_id)

        return OrganizationUsage(
            workspace_count=workspace_count,
            document_count=document_count,
            member_count=member_count,
            storage_bytes=storage_bytes,
        )

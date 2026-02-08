"""HTTP client for the Audit Service internal APIs."""

from datetime import datetime
from uuid import UUID

from chatcraft_common.clients import ServiceClient


class AuditClient(ServiceClient):
    """Client for fetching audit log data from the Audit Service."""

    async def get_workspace_audit(
        self,
        workspace_id: UUID,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """Fetch audit logs for a specific workspace.

        Args:
            workspace_id: The UUID of the workspace.
            page: Page number (1-based).
            page_size: Number of records per page.

        Returns:
            Paginated audit log response dict with 'data' and 'pagination' keys.
        """
        return await self.get(
            f"/internal/audit/workspace/{workspace_id}",
            params={"page": page, "page_size": page_size},
        )

    async def get_org_audit(
        self,
        organization_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """Fetch audit logs for an entire organization.

        Args:
            organization_id: The UUID of the organization.
            start_date: Optional filter for logs after this timestamp.
            end_date: Optional filter for logs before this timestamp.
            page: Page number (1-based).
            page_size: Number of records per page.

        Returns:
            Paginated audit log response dict with 'data' and 'pagination' keys.
        """
        params: dict = {"page": page, "page_size": page_size}
        if start_date is not None:
            params["start_date"] = start_date.isoformat()
        if end_date is not None:
            params["end_date"] = end_date.isoformat()

        return await self.get(
            f"/internal/audit/organization/{organization_id}",
            params=params,
        )

"""HTTP client for the Workspace Service internal APIs."""

from uuid import UUID

from chatcraft_common.clients import ServiceClient


class WorkspaceClient(ServiceClient):
    """Client for fetching session and workspace data from the Workspace Service."""

    async def get_session(self, session_id: UUID) -> dict:
        """Fetch a query session with its messages.

        Args:
            session_id: The UUID of the session to retrieve.

        Returns:
            Session data dict including messages and metadata.
        """
        return await self.get(f"/internal/sessions/{session_id}")

    async def get_workspace(self, workspace_id: UUID) -> dict:
        """Fetch workspace metadata.

        Args:
            workspace_id: The UUID of the workspace.

        Returns:
            Workspace data dict with name and settings.
        """
        return await self.get(f"/internal/workspaces/{workspace_id}")

    async def check_access(self, workspace_id: UUID, user_id: UUID) -> dict:
        """Check whether a user has access to a workspace.

        Args:
            workspace_id: The UUID of the workspace.
            user_id: The UUID of the user to check.

        Returns:
            Access check result dict (includes 'has_access' boolean and 'role').
        """
        return await self.get(
            f"/internal/workspaces/{workspace_id}/access",
            params={"user_id": str(user_id)},
        )

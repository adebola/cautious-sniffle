"""Workspace permission service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import ForbiddenException

from app.models.member import WorkspaceMember
from app.repositories.member_repository import MemberRepository


ROLE_LEVELS: dict[str, int] = {
    "owner": 4,
    "admin": 3,
    "member": 2,
    "viewer": 1,
}


class WorkspacePermissionService:
    """Handle workspace-level permission checks."""

    def __init__(self, member_repo: MemberRepository | None = None):
        self.member_repo = member_repo or MemberRepository()

    async def check_access(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        required_role: str | None = None,
    ) -> WorkspaceMember:
        """Check if user has access to the workspace.

        Args:
            session: Database session.
            workspace_id: The workspace to check.
            user_id: The user requesting access.
            required_role: If set, the user must have at least this role level.

        Returns:
            The member record.

        Raises:
            ForbiddenException: If the user is not a member or lacks the required role.
        """
        member = await self.member_repo.get_by_workspace_and_user(
            session, workspace_id, user_id
        )
        if not member:
            raise ForbiddenException("You are not a member of this workspace")

        if required_role:
            required_level = ROLE_LEVELS.get(required_role, 0)
            user_level = ROLE_LEVELS.get(member.role, 0)
            if user_level < required_level:
                raise ForbiddenException(
                    f"Requires at least '{required_role}' role in this workspace"
                )

        return member

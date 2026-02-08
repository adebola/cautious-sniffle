"""Workspace member business logic service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import (
    ConflictException,
    ErrorCode,
    ForbiddenException,
    NotFoundException,
)

from app.models.member import WorkspaceMember
from app.repositories.member_repository import MemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.member import MemberResponse
from app.services.permission_service import WorkspacePermissionService


class MemberService:
    """Business logic for workspace member operations."""

    def __init__(
        self,
        member_repo: MemberRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
        permission_service: WorkspacePermissionService | None = None,
    ):
        self.member_repo = member_repo or MemberRepository()
        self.workspace_repo = workspace_repo or WorkspaceRepository()
        self.permission_service = permission_service or WorkspacePermissionService(
            member_repo=self.member_repo
        )

    async def add_member(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: str,
    ) -> MemberResponse:
        """Add a member to the workspace (admin+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="admin"
        )

        # Cannot add someone who is already a member
        existing = await self.member_repo.get_by_workspace_and_user(
            session, workspace_id, target_user_id
        )
        if existing:
            raise ConflictException(
                code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                message="User is already a member of this workspace",
            )

        # Non-owners cannot add owners
        if role == "owner":
            raise ForbiddenException("Only the workspace owner can assign the owner role")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=role,
            added_by=user_id,
        )

        member = await self.member_repo.create(session, member)
        return MemberResponse.model_validate(member)

    async def remove_member(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """Remove a member from the workspace (admin+ required, cannot remove owner)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="admin"
        )

        # Check the target member exists
        target_member = await self.member_repo.get_by_workspace_and_user(
            session, workspace_id, target_user_id
        )
        if not target_member:
            raise NotFoundException(
                code=ErrorCode.ORG_USER_NOT_FOUND,
                message="User is not a member of this workspace",
            )

        # Cannot remove the owner
        if target_member.role == "owner":
            raise ForbiddenException("Cannot remove the workspace owner")

        await self.member_repo.delete(session, workspace_id, target_user_id)

    async def update_role(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
    ) -> MemberResponse:
        """Update a member's role (owner only)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="owner"
        )

        # Check the target member exists
        target_member = await self.member_repo.get_by_workspace_and_user(
            session, workspace_id, target_user_id
        )
        if not target_member:
            raise NotFoundException(
                code=ErrorCode.ORG_USER_NOT_FOUND,
                message="User is not a member of this workspace",
            )

        # Cannot change the owner's own role via this endpoint
        if target_member.role == "owner" and user_id == target_user_id:
            raise ForbiddenException("Cannot change your own owner role")

        updated = await self.member_repo.update_role(
            session, workspace_id, target_user_id, new_role
        )
        return MemberResponse.model_validate(updated)

    async def list_members(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[MemberResponse]:
        """List members of a workspace (viewer+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="viewer"
        )

        members = await self.member_repo.list_by_workspace(session, workspace_id)
        return [MemberResponse.model_validate(m) for m in members]

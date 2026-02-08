"""Workspace business logic service."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import ErrorCode, NotFoundException, ConflictException

from app.models.document import WorkspaceDocument
from app.models.member import WorkspaceMember
from app.models.workspace import Workspace
from app.repositories.template_repository import TemplateRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    DocumentAddRequest,
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceDocumentResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.permission_service import WorkspacePermissionService


class WorkspaceService:
    """Business logic for workspace operations."""

    def __init__(
        self,
        workspace_repo: WorkspaceRepository | None = None,
        template_repo: TemplateRepository | None = None,
        permission_service: WorkspacePermissionService | None = None,
    ):
        self.workspace_repo = workspace_repo or WorkspaceRepository()
        self.template_repo = template_repo or TemplateRepository()
        self.permission_service = permission_service or WorkspacePermissionService()

    async def _build_workspace_response(
        self,
        session: AsyncSession,
        workspace: Workspace,
    ) -> WorkspaceResponse:
        doc_count = await self.workspace_repo.get_document_count(session, workspace.id)
        member_count = await self.workspace_repo.get_member_count(session, workspace.id)
        session_count = await self.workspace_repo.get_session_count(session, workspace.id)

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            template_id=workspace.template_id,
            template_name=workspace.template.name if workspace.template else workspace.template_id,
            status=workspace.status,
            document_count=doc_count,
            member_count=member_count,
            session_count=session_count,
            created_by=workspace.created_by,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    async def _build_workspace_detail_response(
        self,
        session: AsyncSession,
        workspace: Workspace,
        current_user_role: str,
    ) -> WorkspaceDetailResponse:
        doc_count = await self.workspace_repo.get_document_count(session, workspace.id)
        member_count = await self.workspace_repo.get_member_count(session, workspace.id)
        session_count = await self.workspace_repo.get_session_count(session, workspace.id)

        return WorkspaceDetailResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            template_id=workspace.template_id,
            template_name=workspace.template.name if workspace.template else workspace.template_id,
            status=workspace.status,
            document_count=doc_count,
            member_count=member_count,
            session_count=session_count,
            created_by=workspace.created_by,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            system_prompt_override=workspace.system_prompt_override,
            settings=workspace.settings or {},
            current_user_role=current_user_role,
        )

    async def create_workspace(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        create_req: WorkspaceCreate,
    ) -> WorkspaceResponse:
        """Create a new workspace and add the creator as owner."""
        # Validate template exists
        template = await self.template_repo.get_by_id(session, create_req.template_id)
        if not template:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message=f"Template '{create_req.template_id}' not found",
            )

        # Merge template default settings with any overrides
        merged_settings = dict(template.default_settings)
        if create_req.settings:
            merged_settings.update(create_req.settings)

        workspace = Workspace(
            organization_id=org_id,
            name=create_req.name,
            description=create_req.description,
            template_id=create_req.template_id,
            system_prompt_override=create_req.system_prompt_override,
            settings=merged_settings,
            status="active",
            created_by=user_id,
        )

        workspace = await self.workspace_repo.create(session, workspace)

        # Add creator as owner
        owner_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role="owner",
            added_by=user_id,
        )
        session.add(owner_member)
        await session.flush()

        return await self._build_workspace_response(session, workspace)

    async def list_workspaces(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[WorkspaceResponse], int]:
        """List workspaces where the user is a member."""
        offset = (page - 1) * page_size
        workspaces, total = await self.workspace_repo.list_by_user_membership(
            session, org_id, user_id, status, offset, page_size
        )

        items = []
        for ws in workspaces:
            resp = await self._build_workspace_response(session, ws)
            items.append(resp)

        return items, total

    async def get_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceDetailResponse:
        """Get workspace detail (requires membership)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        member = await self.permission_service.check_access(
            session, workspace_id, user_id
        )

        return await self._build_workspace_detail_response(
            session, workspace, member.role
        )

    async def update_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        update_req: WorkspaceUpdate,
    ) -> WorkspaceDetailResponse:
        """Update workspace (admin+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        member = await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="admin"
        )

        update_data = update_req.model_dump(exclude_unset=True)
        if update_data:
            workspace = await self.workspace_repo.update_workspace(
                session, workspace_id, **update_data
            )

        return await self._build_workspace_detail_response(
            session, workspace, member.role
        )

    async def archive_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceDetailResponse:
        """Archive workspace (admin+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        member = await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="admin"
        )

        workspace = await self.workspace_repo.update_workspace(
            session,
            workspace_id,
            status="archived",
            archived_at=datetime.now(timezone.utc),
        )

        return await self._build_workspace_detail_response(
            session, workspace, member.role
        )

    async def restore_workspace(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceDetailResponse:
        """Restore an archived workspace (admin+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        member = await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="admin"
        )

        workspace = await self.workspace_repo.update_workspace(
            session,
            workspace_id,
            status="active",
            archived_at=None,
        )

        return await self._build_workspace_detail_response(
            session, workspace, member.role
        )

    async def add_document(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        add_req: DocumentAddRequest,
    ) -> WorkspaceDocumentResponse:
        """Add a document to the workspace (member+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="member"
        )

        # Check if document is already in workspace
        existing = await self.workspace_repo.get_document(
            session, workspace_id, add_req.document_id
        )
        if existing:
            raise ConflictException(
                code=ErrorCode.WS_DOCUMENT_NOT_IN_WORKSPACE,
                message="Document is already in this workspace",
            )

        ws_doc = WorkspaceDocument(
            workspace_id=workspace_id,
            document_id=add_req.document_id,
            added_by=user_id,
            notes=add_req.notes,
            is_primary=add_req.is_primary,
        )

        ws_doc = await self.workspace_repo.add_document(session, ws_doc)
        return WorkspaceDocumentResponse.model_validate(ws_doc)

    async def remove_document(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        """Remove a document from the workspace (member+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="member"
        )

        removed = await self.workspace_repo.remove_document(
            session, workspace_id, document_id
        )
        if not removed:
            raise NotFoundException(
                code=ErrorCode.WS_DOCUMENT_NOT_IN_WORKSPACE,
                message="Document not found in this workspace",
            )

    async def list_documents(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[WorkspaceDocumentResponse]:
        """List documents in a workspace (viewer+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="viewer"
        )

        docs = await self.workspace_repo.list_documents(session, workspace_id)
        return [WorkspaceDocumentResponse.model_validate(d) for d in docs]

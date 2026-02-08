"""Query session business logic service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import ErrorCode, NotFoundException

from app.models.message import Message
from app.models.session import QuerySession
from app.repositories.session_repository import SessionRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.session import SessionCreate, SessionDetailResponse, SessionResponse
from app.services.permission_service import WorkspacePermissionService


class SessionService:
    """Business logic for query session operations."""

    def __init__(
        self,
        session_repo: SessionRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
        permission_service: WorkspacePermissionService | None = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.workspace_repo = workspace_repo or WorkspaceRepository()
        self.permission_service = permission_service or WorkspacePermissionService()

    async def create_session(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        create_req: SessionCreate,
    ) -> SessionResponse:
        """Create a new query session (member+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="member"
        )

        query_session = QuerySession(
            workspace_id=workspace_id,
            user_id=user_id,
            title=create_req.title,
            description=create_req.description,
            selected_document_ids=create_req.selected_document_ids or [],
            status="active",
        )

        query_session = await self.session_repo.create(session, query_session)
        return SessionResponse.model_validate(query_session)

    async def list_sessions(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SessionResponse]:
        """List sessions in a workspace (viewer+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="viewer"
        )

        sessions = await self.session_repo.list_by_workspace(session, workspace_id)
        return [SessionResponse.model_validate(s) for s in sessions]

    async def get_session(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SessionDetailResponse:
        """Get session with messages (viewer+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="viewer"
        )

        query_session = await self.session_repo.get_by_id_with_messages(
            session, session_id
        )
        if not query_session or query_session.workspace_id != workspace_id:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Session not found in this workspace",
            )

        messages = [
            MessageResponse.model_validate(m) for m in query_session.messages
        ]

        return SessionDetailResponse(
            id=query_session.id,
            workspace_id=query_session.workspace_id,
            user_id=query_session.user_id,
            title=query_session.title,
            description=query_session.description,
            selected_document_ids=query_session.selected_document_ids or [],
            status=query_session.status,
            created_at=query_session.created_at,
            updated_at=query_session.updated_at,
            messages=messages,
        )

    async def get_messages(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[MessageResponse]:
        """Get messages for a session (viewer+ required)."""
        workspace = await self.workspace_repo.get_by_id(session, workspace_id)
        if not workspace:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Workspace not found",
            )

        await self.permission_service.check_access(
            session, workspace_id, user_id, required_role="viewer"
        )

        query_session = await self.session_repo.get_by_id(session, session_id)
        if not query_session or query_session.workspace_id != workspace_id:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Session not found in this workspace",
            )

        messages = await self.session_repo.list_messages(session, session_id)
        return [MessageResponse.model_validate(m) for m in messages]

    async def add_message(
        self,
        session: AsyncSession,
        session_id: uuid.UUID,
        data: MessageCreate,
    ) -> MessageResponse:
        """Add a message to a session (internal use by query service)."""
        query_session = await self.session_repo.get_by_id(session, session_id)
        if not query_session:
            raise NotFoundException(
                code=ErrorCode.WS_NOT_FOUND,
                message="Session not found",
            )

        message = Message(
            session_id=session_id,
            role=data.role,
            content=data.content,
            citations=data.citations or [],
            retrieved_chunks=data.retrieved_chunks or [],
            model_used=data.model_used,
            token_count_input=data.token_count_input,
            token_count_output=data.token_count_output,
            latency_ms=data.latency_ms,
        )

        message = await self.session_repo.add_message(session, message)
        return MessageResponse.model_validate(message)

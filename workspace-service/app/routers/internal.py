"""Internal router - /internal/workspaces.

These endpoints are called by other services (e.g. Query Service) and
are NOT exposed through the API Gateway.  No user auth headers required.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_permission_service,
    get_session_service,
    get_workspace_repo,
)
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.message import MessageCreate
from app.services.permission_service import WorkspacePermissionService
from app.services.session_service import SessionService

router = APIRouter(prefix="/internal/workspaces", tags=["internal"])


@router.get("/{workspace_id}/access-check")
async def check_access(
    workspace_id: UUID,
    user_id: UUID = Query(...),
    required_role: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    perm_svc: WorkspacePermissionService = Depends(get_permission_service),
):
    """Check whether a user has access to a workspace.

    Returns the member record if access is granted; raises 403 otherwise.
    """
    member = await perm_svc.check_access(
        db, workspace_id, user_id, required_role=required_role
    )
    return {
        "data": {
            "workspace_id": str(workspace_id),
            "user_id": str(member.user_id),
            "role": member.role,
            "has_access": True,
        }
    }


@router.get("/{workspace_id}/document-ids")
async def get_document_ids(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: WorkspaceRepository = Depends(get_workspace_repo),
):
    """Return the list of document UUIDs attached to a workspace."""
    doc_ids = await repo.get_document_ids(db, workspace_id)
    return {"data": [str(d) for d in doc_ids]}


@router.post("/sessions/{session_id}/messages", status_code=201)
async def add_message(
    session_id: UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    """Add a message to a session (called by the Query Service)."""
    result = await svc.add_message(db, session_id, body)
    return {"data": result.model_dump(mode="json")}

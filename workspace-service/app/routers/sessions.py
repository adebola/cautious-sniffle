"""Sessions router - /api/v1/workspaces/{workspace_id}/sessions."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, get_current_user

from app.dependencies import get_db, get_session_service
from app.schemas.session import SessionCreate
from app.services.session_service import SessionService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/sessions", tags=["sessions"]
)


@router.post("/", status_code=201)
async def create_session(
    workspace_id: UUID,
    body: SessionCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    result = await svc.create_session(db, workspace_id, user.user_id, body)
    return {"data": result.model_dump(mode="json")}


@router.get("/")
async def list_sessions(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    result = await svc.list_sessions(db, workspace_id, user.user_id)
    return {"data": [s.model_dump(mode="json") for s in result]}


@router.get("/{session_id}")
async def get_session(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    result = await svc.get_session(db, workspace_id, session_id, user.user_id)
    return {"data": result.model_dump(mode="json")}


@router.get("/{session_id}/messages")
async def get_messages(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    result = await svc.get_messages(db, workspace_id, session_id, user.user_id)
    return {"data": [m.model_dump(mode="json") for m in result]}

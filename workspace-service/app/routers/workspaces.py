"""Workspace router - /api/v1/workspaces."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, get_current_user
from chatcraft_common.pagination import PaginatedResponse

from app.dependencies import get_db, get_member_service, get_workspace_service
from app.schemas.member import MemberAddRequest, MemberResponse, MemberRoleUpdateRequest
from app.schemas.workspace import (
    DocumentAddRequest,
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceDocumentResponse,
    WorkspaceUpdate,
)
from app.services.member_service import MemberService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


# ──────────────────────────── Workspace CRUD ────────────────────────────


@router.post("/", status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.create_workspace(db, user.organization_id, user.user_id, body)
    return {"data": result.model_dump(mode="json")}


@router.get("/")
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(active|archived|deleted)$"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    items, total = await svc.list_workspaces(
        db, user.organization_id, user.user_id, page, page_size, status
    )
    return PaginatedResponse.create(
        items=[i.model_dump(mode="json") for i in items],
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump(mode="json")


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.get_workspace(db, workspace_id, user.user_id)
    return {"data": result.model_dump(mode="json")}


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.update_workspace(db, workspace_id, user.user_id, body)
    return {"data": result.model_dump(mode="json")}


@router.post("/{workspace_id}/archive")
async def archive_workspace(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.archive_workspace(db, workspace_id, user.user_id)
    return {"data": result.model_dump(mode="json")}


@router.post("/{workspace_id}/restore")
async def restore_workspace(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.restore_workspace(db, workspace_id, user.user_id)
    return {"data": result.model_dump(mode="json")}


# ──────────────────────────── Documents ────────────────────────────


@router.post("/{workspace_id}/documents", status_code=201)
async def add_document(
    workspace_id: UUID,
    body: DocumentAddRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.add_document(db, workspace_id, user.user_id, body)
    return {"data": result.model_dump(mode="json")}


@router.delete("/{workspace_id}/documents/{document_id}", status_code=204)
async def remove_document(
    workspace_id: UUID,
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    await svc.remove_document(db, workspace_id, user.user_id, document_id)


@router.get("/{workspace_id}/documents")
async def list_documents(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkspaceService = Depends(get_workspace_service),
):
    result = await svc.list_documents(db, workspace_id, user.user_id)
    return {"data": [d.model_dump(mode="json") for d in result]}


# ──────────────────────────── Members ────────────────────────────


@router.post("/{workspace_id}/members", status_code=201)
async def add_member(
    workspace_id: UUID,
    body: MemberAddRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: MemberService = Depends(get_member_service),
):
    result = await svc.add_member(
        db, workspace_id, user.user_id, body.user_id, body.role
    )
    return {"data": result.model_dump(mode="json")}


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: MemberService = Depends(get_member_service),
):
    await svc.remove_member(db, workspace_id, user.user_id, user_id)


@router.put("/{workspace_id}/members/{user_id}/role")
async def update_member_role(
    workspace_id: UUID,
    user_id: UUID,
    body: MemberRoleUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: MemberService = Depends(get_member_service),
):
    result = await svc.update_role(
        db, workspace_id, user.user_id, user_id, body.role
    )
    return {"data": result.model_dump(mode="json")}


@router.get("/{workspace_id}/members")
async def list_members(
    workspace_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: MemberService = Depends(get_member_service),
):
    result = await svc.list_members(db, workspace_id, user.user_id)
    return {"data": [m.model_dump(mode="json") for m in result]}

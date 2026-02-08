"""User and invitation management endpoints.

Endpoints that mutate users or manage invitations require admin/owner role.
Listing and reading users is available to all authenticated members.

IMPORTANT: Static path segments (/invite, /invitations, /invitations/accept)
are registered BEFORE the dynamic /{user_id} routes so that FastAPI matches
them first rather than trying to parse "invite" / "invitations" as a UUID.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, require_role
from chatcraft_common.errors import ChatCraftException, ErrorCode, ForbiddenException

from app.config import Settings
from app.dependencies import get_current_user, get_db, get_settings
from app.repositories.user_repository import InvitationRepository
from app.schemas.invitation import AcceptInviteRequest, InviteRequest
from app.schemas.user import RoleUpdate, UserCreate, UserUpdate
from app.services.invitation_service import InvitationService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _user_service(settings: Settings) -> UserService:
    return UserService(settings)


def _invitation_service(settings: Settings, db: AsyncSession) -> InvitationService:
    repo = InvitationRepository(db)
    return InvitationService(settings, repo)


# ========================================================================== #
#  Invitations -- must be registered before /{user_id} routes
# ========================================================================== #

@router.post("/invite", response_model=dict, status_code=201)
async def invite_user(
    body: InviteRequest,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Send an invitation to join the organization (admin/owner only)."""
    service = _invitation_service(settings, db)
    result = await service.invite_user(
        org_id=user.organization_id,
        invite=body,
        invited_by=user.user_id,
    )
    return {"data": result.model_dump(mode="json")}


@router.get("/invitations", response_model=dict)
async def list_invitations(
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """List pending invitations for the current organization (admin/owner only)."""
    service = _invitation_service(settings, db)
    invitations = await service.list_invitations(user.organization_id)
    return {"data": [inv.model_dump(mode="json") for inv in invitations]}


@router.post("/invitations/accept", response_model=dict, status_code=201)
async def accept_invitation(
    body: AcceptInviteRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation (public -- no auth required)."""
    service = _invitation_service(settings, db)
    result = await service.accept_invitation(body)
    return {"data": result.model_dump(mode="json")}


@router.delete("/invitations/{invitation_id}", status_code=204)
async def cancel_invitation(
    invitation_id: UUID,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending invitation (admin/owner only)."""
    service = _invitation_service(settings, db)
    await service.cancel_invitation(user.organization_id, invitation_id)


# ========================================================================== #
#  User CRUD
# ========================================================================== #

@router.get("", response_model=dict)
async def list_users(
    search: str | None = Query(None, min_length=1, max_length=200),
    status: str | None = Query(None, pattern="^(active|suspended|deactivated)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """List users in the current organization with optional search and filtering."""
    service = _user_service(settings)
    result = await service.list_users(
        org_id=user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )
    return {
        "data": [u.model_dump(mode="json") for u in result.data],
        "meta": result.meta.model_dump(),
    }


@router.post("", response_model=dict, status_code=201)
async def create_user(
    body: UserCreate,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
):
    """Create a new user in the organization (admin/owner only)."""
    service = _user_service(settings)
    result = await service.create_user(user.organization_id, body)
    return {"data": result.model_dump(mode="json")}


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Get a specific user by ID."""
    service = _user_service(settings)
    result = await service.get_user(user.organization_id, user_id)
    return {"data": result.model_dump(mode="json")}


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
):
    """Update a user in the organization (admin/owner only)."""
    service = _user_service(settings)
    result = await service.update_user(user.organization_id, user_id, body)
    return {"data": result.model_dump(mode="json")}


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
):
    """Soft-delete a user (admin/owner only). Cannot delete self or owner."""
    if user_id == user.user_id:
        raise ChatCraftException(
            status_code=400,
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            message="You cannot delete your own account",
        )

    # Fetch target user to check their role
    service = _user_service(settings)
    target = await service.get_user(user.organization_id, user_id)

    if target.role == "owner":
        raise ForbiddenException(message="The organization owner cannot be deleted")

    await service.delete_user(user.organization_id, user_id)


@router.put("/{user_id}/role", response_model=dict)
async def change_user_role(
    user_id: UUID,
    body: RoleUpdate,
    user: CurrentUser = Depends(require_role("owner")),
    settings: Settings = Depends(get_settings),
):
    """Change a user's role (owner only)."""
    if user_id == user.user_id:
        raise ChatCraftException(
            status_code=400,
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            message="You cannot change your own role",
        )

    service = _user_service(settings)
    update_data = UserUpdate(role=body.role)
    result = await service.update_user(user.organization_id, user_id, update_data)
    return {"data": result.model_dump(mode="json")}

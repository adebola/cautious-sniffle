"""Internal endpoints for inter-service communication.

These endpoints are called by other microservices (not by the gateway)
and therefore do NOT require authentication headers. They should be
network-isolated in production (e.g., only reachable from the internal
service mesh).
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import get_db, get_settings
from app.repositories.organization_repository import OrganizationSettingsRepository
from app.services.organization_service import OrganizationService
from app.services.user_service import UserService

router = APIRouter(prefix="/internal", tags=["internal"])


# --------------------------------------------------------------------------- #
# GET /internal/organizations/{org_id}
# --------------------------------------------------------------------------- #
@router.get("/organizations/{org_id}", response_model=dict)
async def get_organization(
    org_id: UUID,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Return organization data for use by other services."""
    repo = OrganizationSettingsRepository(db)
    service = OrganizationService(settings, org_settings_repo=repo)
    org = await service.get_current_organization(org_id)
    return {"data": org.model_dump(mode="json")}


# --------------------------------------------------------------------------- #
# GET /internal/users/{user_id}
# --------------------------------------------------------------------------- #
@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: UUID,
    org_id: UUID | None = None,
    settings: Settings = Depends(get_settings),
):
    """Return user data for use by other services.

    If ``org_id`` is provided the lookup is scoped to that organization.
    Otherwise the auth service is queried by user ID alone.
    """
    service = UserService(settings)
    if org_id is not None:
        user = await service.get_user(org_id, user_id)
    else:
        # Fall back to a direct user lookup via auth service
        from chatcraft_common.clients import ServiceClient

        client = ServiceClient(settings.auth_service_url)
        import httpx
        from chatcraft_common.errors import ErrorCode, NotFoundException

        try:
            response = await client.get(f"/internal/users/{user_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_USER_NOT_FOUND,
                    message=f"User {user_id} not found",
                )
            raise
        user_data = response.get("data", response)
        from app.schemas.user import UserResponse

        user = UserResponse(**user_data)

    return {"data": user.model_dump(mode="json")}

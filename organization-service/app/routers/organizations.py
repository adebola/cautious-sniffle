"""Organization management endpoints.

All endpoints operate on the *current* user's organization (derived from the
authenticated user's ``organization_id`` header forwarded by the gateway).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, require_role

from app.config import Settings
from app.dependencies import get_current_user, get_db, get_settings
from app.repositories.organization_repository import OrganizationSettingsRepository
from app.schemas.organization import OrganizationUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


def _org_service(settings: Settings, db: AsyncSession) -> OrganizationService:
    """Build an OrganizationService wired to the current request."""
    repo = OrganizationSettingsRepository(db)
    return OrganizationService(settings, org_settings_repo=repo)


# --------------------------------------------------------------------------- #
# GET /api/v1/organizations/current
# --------------------------------------------------------------------------- #
@router.get("/current", response_model=dict)
async def get_current_organization(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's organization."""
    service = _org_service(settings, db)
    org = await service.get_current_organization(user.organization_id)
    return {"data": org.model_dump(mode="json")}


# --------------------------------------------------------------------------- #
# PUT /api/v1/organizations/current
# --------------------------------------------------------------------------- #
@router.put("/current", response_model=dict)
async def update_current_organization(
    body: OrganizationUpdate,
    user: CurrentUser = Depends(require_role("owner", "admin")),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's organization (admin/owner only)."""
    service = _org_service(settings, db)
    org = await service.update_organization(user.organization_id, body)
    return {"data": org.model_dump(mode="json")}


# --------------------------------------------------------------------------- #
# GET /api/v1/organizations/current/usage
# --------------------------------------------------------------------------- #
@router.get("/current/usage", response_model=dict)
async def get_organization_usage(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated usage statistics for the current organization."""
    service = _org_service(settings, db)
    usage = await service.get_organization_usage(user.organization_id)
    return {"data": usage.model_dump()}

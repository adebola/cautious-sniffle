"""Public-facing audit log endpoints (admin/owner only)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from chatcraft_common.auth import CurrentUser, require_role
from chatcraft_common.pagination import PaginatedResponse

from app.dependencies import get_audit_service
from app.models.audit_log import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/", response_model=dict)
async def query_audit_logs(
    workspace_id: UUID | None = Query(None, description="Filter by workspace"),
    user_id: UUID | None = Query(None, description="Filter by user"),
    action: str | None = Query(None, description="Filter by action (e.g. workspace.created)"),
    resource_type: str | None = Query(None, description="Filter by resource type (e.g. workspace)"),
    start_date: datetime | None = Query(None, description="Start of date range (inclusive)"),
    end_date: datetime | None = Query(None, description="End of date range (inclusive)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: CurrentUser = Depends(require_role("admin", "owner")),
    service: AuditService = Depends(get_audit_service),
):
    """Query audit logs for the authenticated user's organization.

    Only organization admins and owners can access audit logs.
    """
    items, total = await service.query_logs(
        organization_id=user.organization_id,
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    data = [AuditLogResponse(**item).model_dump(mode="json") for item in items]
    return PaginatedResponse.create(
        items=data,
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump(mode="json")


@router.get("/{log_id}", response_model=dict)
async def get_audit_log(
    log_id: str,
    user: CurrentUser = Depends(require_role("admin", "owner")),
    service: AuditService = Depends(get_audit_service),
):
    """Retrieve a single audit log entry by ID.

    Only organization admins and owners can access audit logs.
    The entry must belong to the authenticated user's organization.
    """
    entry = await service.get_log(log_id=log_id, organization_id=user.organization_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit log entry not found")

    data = AuditLogResponse(**entry).model_dump(mode="json")
    return {"data": data}

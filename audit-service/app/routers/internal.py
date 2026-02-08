"""Internal endpoints consumed by other microservices (not routed via Gateway)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from chatcraft_common.pagination import PaginatedResponse

from app.dependencies import get_audit_service
from app.models.audit_log import AuditLogCreate, AuditLogResponse
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/audit", tags=["internal"])


@router.post("/log", response_model=dict, status_code=201)
async def create_audit_log(
    body: AuditLogCreate,
    service: AuditService = Depends(get_audit_service),
):
    """Receive an audit event from another service and persist it.

    This endpoint has no authentication; it is intended for internal
    service-to-service communication only and should not be exposed
    through the API Gateway.
    """
    log_id = await service.log_event(body)
    return {"data": {"id": log_id}}


@router.get("/workspace/{workspace_id}", response_model=dict)
async def get_workspace_audit_logs(
    workspace_id: UUID,
    organization_id: UUID = Query(..., description="Organization ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: AuditService = Depends(get_audit_service),
):
    """Get audit logs for a specific workspace.

    Called by the workspace service to display workspace activity.
    No authentication; internal use only.
    """
    items, total = await service.get_workspace_audit(
        workspace_id=workspace_id,
        organization_id=organization_id,
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

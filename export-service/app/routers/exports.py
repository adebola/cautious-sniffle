"""Public-facing export endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from chatcraft_common.auth import CurrentUser, get_current_user, require_role

from app.dependencies import get_export_service
from app.schemas.export import AuditExportFormat, ExportFormat
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.post("/sessions/{session_id}")
async def export_session(
    session_id: UUID,
    format: ExportFormat = Query(default=ExportFormat.DOCX),
    user: CurrentUser = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
):
    """Export a query session as DOCX, PDF, or Markdown.

    The authenticated user must have access to the workspace that owns
    the session.  The response is a streaming file download.
    """
    file_bytes, filename, content_type = await service.export_session(
        session_id=session_id,
        format=format.value,
        user_id=user.user_id,
        organization_id=user.organization_id,
    )

    return StreamingResponse(
        file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/audit")
async def export_audit_logs(
    workspace_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    format: AuditExportFormat = Query(default=AuditExportFormat.CSV),
    user: CurrentUser = Depends(require_role("admin", "owner")),
    service: ExportService = Depends(get_export_service),
):
    """Export audit logs as CSV or XLSX.

    Only users with the *admin* or *owner* role may access this endpoint.
    When ``workspace_id`` is provided the export is scoped to that
    workspace; otherwise the full organization audit log is exported.
    """
    file_bytes, filename, content_type = await service.export_audit_logs(
        organization_id=user.organization_id,
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
        format=format.value,
    )

    return StreamingResponse(
        file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

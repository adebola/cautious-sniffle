"""Main orchestration service for exports."""

import logging
import re
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException
from httpx import HTTPStatusError

from app.clients.audit_client import AuditClient
from app.clients.workspace_client import WorkspaceClient
from app.services.csv_exporter import CsvExporter
from app.services.docx_exporter import DocxExporter
from app.services.markdown_exporter import MarkdownExporter
from app.services.pdf_exporter import PdfExporter
from app.services.xlsx_exporter import XlsxExporter

logger = logging.getLogger(__name__)

# Content-type mapping for session exports
_SESSION_CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "markdown": "text/markdown; charset=utf-8",
}

# File extension mapping for session exports
_SESSION_EXTENSIONS = {
    "docx": "docx",
    "pdf": "pdf",
    "markdown": "md",
}

# Content-type mapping for audit exports
_AUDIT_CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ExportService:
    """Orchestrates fetching data from other services and delegating to exporters."""

    def __init__(
        self,
        workspace_client: WorkspaceClient,
        audit_client: AuditClient,
    ):
        self._workspace_client = workspace_client
        self._audit_client = audit_client

        # Eagerly instantiate exporters (they are lightweight)
        self._docx_exporter = DocxExporter()
        self._pdf_exporter = PdfExporter()
        self._markdown_exporter = MarkdownExporter()
        self._csv_exporter = CsvExporter()
        self._xlsx_exporter = XlsxExporter()

    async def export_session(
        self,
        session_id: UUID,
        format: str,
        user_id: UUID,
        organization_id: UUID,
    ) -> tuple[BytesIO, str, str]:
        """Export a query session in the requested format.

        Args:
            session_id: The UUID of the session to export.
            format: One of "docx", "pdf", "markdown".
            user_id: The requesting user's UUID (for access checks).
            organization_id: The user's organization UUID.

        Returns:
            A tuple of (file_bytes, filename, content_type).

        Raises:
            HTTPException: On access denied, session not found, or upstream errors.
        """
        # 1. Fetch session data (includes messages)
        try:
            session_data = await self._workspace_client.get_session(session_id)
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Session not found")
            logger.error("Failed to fetch session %s: %s", session_id, exc)
            raise HTTPException(status_code=502, detail="Failed to fetch session data")

        workspace_id = session_data.get("workspace_id")
        if not workspace_id:
            raise HTTPException(status_code=500, detail="Session has no associated workspace")

        # 2. Verify user has access to the workspace
        try:
            access = await self._workspace_client.check_access(UUID(workspace_id), user_id)
            if not access.get("has_access"):
                raise HTTPException(status_code=403, detail="Access denied to this workspace")
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Workspace not found")
            logger.error("Access check failed for workspace %s: %s", workspace_id, exc)
            raise HTTPException(status_code=502, detail="Failed to verify workspace access")

        # 3. Fetch workspace name
        try:
            workspace_data = await self._workspace_client.get_workspace(UUID(workspace_id))
            workspace_name = workspace_data.get("name", "Workspace")
        except HTTPStatusError:
            logger.warning("Could not fetch workspace name for %s, using fallback", workspace_id)
            workspace_name = "Workspace"

        # 4. Dispatch to the correct exporter
        if format == "docx":
            file_bytes = self._docx_exporter.export_session(session_data, workspace_name)
        elif format == "pdf":
            file_bytes = self._pdf_exporter.export_session(session_data, workspace_name)
        elif format == "markdown":
            file_bytes = self._markdown_exporter.export_session(session_data, workspace_name)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        # 5. Build filename
        session_title = session_data.get("title", "session")
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        ext = _SESSION_EXTENSIONS[format]
        safe_ws = self._sanitize_filename(workspace_name)
        safe_title = self._sanitize_filename(session_title)
        filename = f"{safe_ws}_{safe_title}_{date_str}.{ext}"

        content_type = _SESSION_CONTENT_TYPES[format]
        return file_bytes, filename, content_type

    async def export_audit_logs(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        format: str = "csv",
    ) -> tuple[BytesIO, str, str]:
        """Export audit logs in the requested format.

        Fetches all pages of audit data and exports as CSV or XLSX.

        Args:
            organization_id: The organization UUID for org-wide audits.
            workspace_id: Optional workspace UUID to scope audit logs.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            format: One of "csv", "xlsx".

        Returns:
            A tuple of (file_bytes, filename, content_type).

        Raises:
            HTTPException: On upstream fetch errors.
        """
        all_logs: list[dict] = []
        page = 1
        page_size = 200

        try:
            while True:
                if workspace_id is not None:
                    result = await self._audit_client.get_workspace_audit(
                        workspace_id=workspace_id,
                        page=page,
                        page_size=page_size,
                    )
                else:
                    result = await self._audit_client.get_org_audit(
                        organization_id=organization_id,
                        start_date=start_date,
                        end_date=end_date,
                        page=page,
                        page_size=page_size,
                    )

                data = result.get("data", [])
                all_logs.extend(data)

                # Check if there are more pages
                pagination = result.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)
                if page >= total_pages or not data:
                    break
                page += 1

        except HTTPStatusError as exc:
            logger.error("Failed to fetch audit logs: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to fetch audit log data")

        # Dispatch to exporter
        if format == "csv":
            file_bytes = self._csv_exporter.export_audit_logs(all_logs)
        elif format == "xlsx":
            file_bytes = self._xlsx_exporter.export_audit_logs(all_logs)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        # Build filename
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        ext = format
        filename = f"audit_export_{date_str}.{ext}"

        content_type = _AUDIT_CONTENT_TYPES[format]
        return file_bytes, filename, content_type

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove or replace characters that are unsafe in filenames."""
        sanitized = re.sub(r"[^\w\s-]", "", name)
        sanitized = re.sub(r"[\s]+", "_", sanitized)
        return sanitized.strip("_")[:80] or "export"

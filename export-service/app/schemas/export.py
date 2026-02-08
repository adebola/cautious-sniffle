"""Pydantic schemas for export requests."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ExportFormat(StrEnum):
    """Supported export formats for query sessions."""

    DOCX = "docx"
    PDF = "pdf"
    MARKDOWN = "markdown"


class AuditExportFormat(StrEnum):
    """Supported export formats for audit logs."""

    CSV = "csv"
    XLSX = "xlsx"


class SessionExportRequest(BaseModel):
    """Request body for exporting a query session."""

    session_id: UUID
    format: ExportFormat = Field(default=ExportFormat.DOCX)


class AuditExportRequest(BaseModel):
    """Request body for exporting audit logs."""

    workspace_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    format: AuditExportFormat = Field(default=AuditExportFormat.CSV)

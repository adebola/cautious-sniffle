"""Pydantic models for audit log documents."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    """Schema for creating a new audit log entry."""

    organization_id: UUID
    workspace_id: UUID | None = None
    user_id: UUID
    action: str  # e.g., "workspace.created", "document.uploaded", "member.added"
    resource_type: str  # e.g., "workspace", "document", "member"
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogResponse(BaseModel):
    """Schema for returning an audit log entry."""

    id: str
    organization_id: UUID
    workspace_id: UUID | None = None
    user_id: UUID
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

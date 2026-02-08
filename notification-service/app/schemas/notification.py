"""Notification Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """Full notification response returned to clients."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    data: dict = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    """Schema for creating a notification (used by internal endpoints)."""

    organization_id: UUID
    user_id: UUID
    type: str = Field(..., max_length=50, description="Notification type: invitation, workspace_added, document_processed, billing, system")
    title: str = Field(..., max_length=255)
    message: str
    data: dict = Field(default_factory=dict)


class SendEmailRequest(BaseModel):
    """Schema for sending an email (used by internal endpoints)."""

    to_email: str
    to_name: str = ""
    subject: str
    template_name: str
    template_data: dict = Field(default_factory=dict)


class UnreadCountResponse(BaseModel):
    """Response for unread notification count."""

    count: int

"""Session Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class SessionCreate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    selected_document_ids: list[UUID] = Field(default_factory=list)


class SessionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    title: str | None
    description: str | None
    selected_document_ids: list[UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)

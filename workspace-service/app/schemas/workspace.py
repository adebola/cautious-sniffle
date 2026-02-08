"""Workspace Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    template_id: str
    system_prompt_override: str | None = None
    settings: dict | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt_override: str | None = None
    settings: dict | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    template_id: str
    template_name: str
    status: str
    document_count: int
    member_count: int
    session_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceDetailResponse(WorkspaceResponse):
    system_prompt_override: str | None
    settings: dict
    current_user_role: str


class DocumentAddRequest(BaseModel):
    document_id: UUID
    notes: str | None = None
    is_primary: bool = False


class WorkspaceDocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    document_id: UUID
    added_by: UUID
    added_at: datetime
    notes: str | None
    is_primary: bool

    model_config = {"from_attributes": True}

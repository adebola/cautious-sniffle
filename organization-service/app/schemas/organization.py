"""Organization-related request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationResponse(BaseModel):
    """Public representation of an organization."""

    id: UUID
    name: str
    slug: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    status: str
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    """Fields that may be updated on an organization."""

    name: str | None = Field(None, min_length=2, max_length=100)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=30)
    address: str | None = Field(None, max_length=500)
    logo_url: str | None = Field(None, max_length=1024)

    model_config = {"extra": "forbid"}


class OrganizationUsage(BaseModel):
    """Aggregated usage statistics for an organization."""

    workspace_count: int = 0
    document_count: int = 0
    member_count: int = 0
    storage_bytes: int = 0

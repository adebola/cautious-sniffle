"""Member Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemberAddRequest(BaseModel):
    user_id: UUID
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class MemberRoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|member|viewer)$")


class MemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    added_by: UUID
    added_at: datetime

    model_config = {"from_attributes": True}

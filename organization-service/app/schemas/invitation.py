"""Invitation-related request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InviteRequest(BaseModel):
    """Payload for inviting a user to an organization."""

    email: str = Field(..., max_length=255)
    role: str = Field("member", pattern="^(admin|member)$")

    model_config = {"extra": "forbid"}


class InvitationResponse(BaseModel):
    """Public representation of an invitation."""

    id: UUID
    email: str
    role: str
    status: str
    invited_by: UUID
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class AcceptInviteRequest(BaseModel):
    """Payload for accepting an invitation."""

    token: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    model_config = {"extra": "forbid"}

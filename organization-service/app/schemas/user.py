"""User-related request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from chatcraft_common.pagination import PaginatedResponse


class UserResponse(BaseModel):
    """Public representation of an organization member."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    avatar_url: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Payload for creating a new user in the organization."""

    email: str = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field("member", pattern="^(admin|member)$")
    password: str = Field(..., min_length=8, max_length=128)

    model_config = {"extra": "forbid"}


class UserUpdate(BaseModel):
    """Fields that may be updated on a user."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = Field(None, pattern="^(owner|admin|member)$")
    status: str | None = Field(None, pattern="^(active|suspended|deactivated)$")
    avatar_url: str | None = Field(None, max_length=1024)

    model_config = {"extra": "forbid"}


class RoleUpdate(BaseModel):
    """Payload for changing a user's role."""

    role: str = Field(..., pattern="^(admin|member)$")

    model_config = {"extra": "forbid"}


class UserListResponse(PaginatedResponse):
    """Paginated list of users."""

    data: list[UserResponse]  # type: ignore[assignment]

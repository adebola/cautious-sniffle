"""Authentication dependencies for Python services.

The Gateway validates JWT tokens and forwards user identity as headers.
Python services trust these headers (they are only reachable behind the Gateway
or via internal calls).
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException


@dataclass
class CurrentUser:
    user_id: UUID
    organization_id: UUID
    role: str  # "owner", "admin", "member"


async def get_current_user(
    x_user_id: str | None = Header(None),
    x_organization_id: str | None = Header(None),
    x_user_role: str | None = Header(None),
) -> CurrentUser:
    """Extract the authenticated user from Gateway-forwarded headers."""
    if not x_user_id or not x_organization_id or not x_user_role:
        raise HTTPException(status_code=401, detail="Missing authentication headers")
    try:
        return CurrentUser(
            user_id=UUID(x_user_id),
            organization_id=UUID(x_organization_id),
            role=x_user_role,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authentication headers")


def require_role(*allowed_roles: str):
    """Dependency factory that checks the user's org-level role."""

    async def check_role(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return check_role

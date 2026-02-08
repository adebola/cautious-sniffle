"""Service for user management operations.

All user data lives in the auth service. This service proxies CRUD operations
via internal HTTP calls and translates responses into organisation-service schemas.
"""

import logging
from typing import Any
from uuid import UUID

import httpx

from chatcraft_common.clients import ServiceClient
from chatcraft_common.errors import ErrorCode, NotFoundException
from chatcraft_common.pagination import PaginatedResponse

from app.config import Settings
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """Proxy user CRUD to the auth service."""

    def __init__(self, settings: Settings) -> None:
        self._auth_client = ServiceClient(settings.auth_service_url)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------
    async def list_users(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> UserListResponse:
        """Return a paginated list of users in the given organization."""
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if search:
            params["search"] = search
        if status:
            params["status"] = status

        try:
            response = await self._auth_client.get(
                f"/internal/organizations/{org_id}/users",
                params=params,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_NOT_FOUND,
                    message=f"Organization {org_id} not found",
                )
            raise

        items_raw: list[dict[str, Any]] = response.get("data", [])
        meta_raw: dict[str, Any] = response.get("meta", {})

        users = [UserResponse(**u) for u in items_raw]

        return UserListResponse(
            data=users,
            meta={
                "page": meta_raw.get("page", page),
                "page_size": meta_raw.get("page_size", page_size),
                "total": meta_raw.get("total", len(users)),
                "has_more": meta_raw.get("has_more", False),
            },
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    async def get_user(self, org_id: UUID, user_id: UUID) -> UserResponse:
        """Get a single user by ID within the organization."""
        try:
            response = await self._auth_client.get(
                f"/internal/organizations/{org_id}/users/{user_id}"
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_USER_NOT_FOUND,
                    message=f"User {user_id} not found in organization {org_id}",
                )
            raise

        user_data: dict[str, Any] = response.get("data", response)
        return UserResponse(**user_data)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    async def create_user(self, org_id: UUID, user_create: UserCreate) -> UserResponse:
        """Create a new user in the organization via the auth service."""
        payload = user_create.model_dump()
        try:
            response = await self._auth_client.post(
                f"/internal/organizations/{org_id}/users",
                json=payload,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_NOT_FOUND,
                    message=f"Organization {org_id} not found",
                )
            if exc.response.status_code == 409:
                from chatcraft_common.errors import ConflictException
                raise ConflictException(
                    code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                    message=f"User with email {user_create.email} already exists",
                )
            raise

        user_data: dict[str, Any] = response.get("data", response)
        return UserResponse(**user_data)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    async def update_user(
        self, org_id: UUID, user_id: UUID, update_data: UserUpdate
    ) -> UserResponse:
        """Update an existing user via the auth service."""
        payload = update_data.model_dump(exclude_none=True)
        if not payload:
            return await self.get_user(org_id, user_id)

        try:
            response = await self._auth_client.put(
                f"/internal/organizations/{org_id}/users/{user_id}",
                json=payload,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_USER_NOT_FOUND,
                    message=f"User {user_id} not found in organization {org_id}",
                )
            raise

        user_data: dict[str, Any] = response.get("data", response)
        return UserResponse(**user_data)

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------
    async def delete_user(self, org_id: UUID, user_id: UUID) -> None:
        """Soft-delete a user via the auth service."""
        try:
            await self._auth_client.delete(
                f"/internal/organizations/{org_id}/users/{user_id}"
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundException(
                    code=ErrorCode.ORG_USER_NOT_FOUND,
                    message=f"User {user_id} not found in organization {org_id}",
                )
            raise

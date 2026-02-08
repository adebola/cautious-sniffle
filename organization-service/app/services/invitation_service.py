"""Service for invitation lifecycle management.

Invitations are stored in the local chatcraft_org database and are the
primary domain objects owned by this service (as opposed to org/user data
which is proxied from the auth service).
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from chatcraft_common.clients import ServiceClient
from chatcraft_common.errors import (
    ChatCraftException,
    ConflictException,
    ErrorCode,
    NotFoundException,
)

from app.config import Settings
from app.models.invitation import Invitation
from app.repositories.user_repository import InvitationRepository
from app.schemas.invitation import AcceptInviteRequest, InvitationResponse, InviteRequest

logger = logging.getLogger(__name__)

# Token is 48 URL-safe bytes (64 characters base64)
_TOKEN_BYTES = 48


def _hash_token(token: str) -> str:
    """Return a hex-encoded SHA-256 hash of the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InvitationService:
    """Manages the invitation lifecycle: create, list, accept, cancel."""

    def __init__(
        self,
        settings: Settings,
        invitation_repo: InvitationRepository,
    ) -> None:
        self._settings = settings
        self._repo = invitation_repo
        self._auth_client = ServiceClient(settings.auth_service_url)
        self._notification_client = ServiceClient(settings.notification_service_url)

    # ------------------------------------------------------------------
    # Invite
    # ------------------------------------------------------------------
    async def invite_user(
        self,
        org_id: UUID,
        invite: InviteRequest,
        invited_by: UUID,
    ) -> InvitationResponse:
        """Create a new invitation, generate a token, and persist it.

        The raw token is returned in the response so the caller (or a
        future notification service call) can include it in the invite link.
        """
        # Check for an existing pending invitation for the same org + email
        existing = await self._repo.get_by_org_and_email(org_id, invite.email)
        if existing is not None and existing.status == "pending":
            raise ConflictException(
                code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                message=f"A pending invitation already exists for {invite.email}",
            )

        # If a previous invitation was cancelled/expired, remove it so the
        # unique constraint on (org_id, email) does not conflict.
        if existing is not None and existing.status in ("cancelled", "expired"):
            await self._repo.mark_cancelled(existing.id)
            # We need to actually delete the old row to allow re-invite
            from sqlalchemy import delete as sa_delete
            from app.models.invitation import Invitation as InvModel
            await self._repo._session.execute(
                sa_delete(InvModel).where(InvModel.id == existing.id)
            )
            await self._repo._session.flush()

        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        token_hash = _hash_token(raw_token)

        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self._settings.invitation_expiry_hours
        )

        invitation = Invitation(
            organization_id=org_id,
            email=invite.email,
            role=invite.role,
            invited_by=invited_by,
            status="pending",
            token_hash=token_hash,
            expires_at=expires_at,
        )

        invitation = await self._repo.create(invitation)

        # TODO: Call notification service to send invitation email.
        # The email should contain a link like:
        #   {self._settings.invitation_base_url}?token={raw_token}
        logger.info(
            "Invitation created for %s in org %s (token_hash=%s...)",
            invite.email,
            org_id,
            token_hash[:12],
        )

        return InvitationResponse.model_validate(invitation)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------
    async def list_invitations(
        self,
        org_id: UUID,
        status: str | None = "pending",
    ) -> list[InvitationResponse]:
        """Return invitations for an organization, defaulting to pending."""
        # Expire stale invitations before listing
        await self._repo.mark_expired_bulk()

        invitations = await self._repo.list_by_org(org_id, status=status)
        return [InvitationResponse.model_validate(inv) for inv in invitations]

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------
    async def accept_invitation(
        self,
        accept: AcceptInviteRequest,
    ) -> InvitationResponse:
        """Validate the token, create the user in the auth service, and
        mark the invitation as accepted.
        """
        token_hash = _hash_token(accept.token)
        invitation = await self._repo.get_by_token_hash(token_hash)

        if invitation is None:
            raise NotFoundException(
                code=ErrorCode.ORG_NOT_FOUND,
                message="Invalid or expired invitation token",
            )

        if invitation.status != "pending":
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                message=f"Invitation is no longer pending (status={invitation.status})",
            )

        if invitation.expires_at < datetime.now(timezone.utc):
            await self._repo.mark_cancelled(invitation.id)
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.ORG_NOT_FOUND,
                message="Invitation has expired",
            )

        # Create the user in the auth service
        try:
            await self._auth_client.post(
                f"/internal/organizations/{invitation.organization_id}/users",
                json={
                    "email": invitation.email,
                    "first_name": accept.first_name,
                    "last_name": accept.last_name,
                    "password": accept.password,
                    "role": invitation.role,
                },
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                raise ConflictException(
                    code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                    message=f"User with email {invitation.email} already exists in the organization",
                )
            logger.error(
                "Auth service error while creating user for invitation %s: %s",
                invitation.id,
                exc,
            )
            raise ChatCraftException(
                status_code=502,
                code=ErrorCode.ORG_NOT_FOUND,
                message="Failed to create user account. Please try again later.",
            )

        updated = await self._repo.mark_accepted(invitation.id)
        if updated is None:
            # Edge case: concurrent acceptance
            raise ConflictException(
                code=ErrorCode.ORG_USER_ALREADY_EXISTS,
                message="Invitation was already accepted",
            )

        return InvitationResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------
    async def cancel_invitation(
        self,
        org_id: UUID,
        invitation_id: UUID,
    ) -> InvitationResponse:
        """Cancel a pending invitation."""
        invitation = await self._repo.get_by_id(invitation_id)
        if invitation is None or invitation.organization_id != org_id:
            raise NotFoundException(
                code=ErrorCode.ORG_NOT_FOUND,
                message=f"Invitation {invitation_id} not found",
            )

        if invitation.status != "pending":
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.ORG_NOT_FOUND,
                message=f"Cannot cancel invitation with status '{invitation.status}'",
            )

        updated = await self._repo.mark_cancelled(invitation_id)
        if updated is None:
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.ORG_NOT_FOUND,
                message="Failed to cancel invitation (it may have been accepted concurrently)",
            )

        return InvitationResponse.model_validate(updated)

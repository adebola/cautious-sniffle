"""Repository for invitations table operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation


class InvitationRepository:
    """Async CRUD operations for the invitations table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, invitation: Invitation) -> Invitation:
        """Persist a new invitation."""
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None:
        """Return an invitation by its primary key."""
        stmt = select(Invitation).where(Invitation.id == invitation_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        """Return an invitation by its unique token hash."""
        stmt = select(Invitation).where(Invitation.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_org_and_email(
        self, organization_id: UUID, email: str
    ) -> Invitation | None:
        """Return the invitation for a specific org + email combination."""
        stmt = select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.email == email,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: UUID,
        status: str | None = None,
    ) -> list[Invitation]:
        """List invitations for an organization, optionally filtered by status."""
        stmt = select(Invitation).where(
            Invitation.organization_id == organization_id
        ).order_by(Invitation.created_at.desc())

        if status is not None:
            stmt = stmt.where(Invitation.status == status)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_accepted(self, invitation_id: UUID) -> Invitation | None:
        """Mark an invitation as accepted."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Invitation)
            .where(Invitation.id == invitation_id)
            .values(status="accepted", accepted_at=now)
            .returning(Invitation)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_cancelled(self, invitation_id: UUID) -> Invitation | None:
        """Mark an invitation as cancelled."""
        stmt = (
            update(Invitation)
            .where(
                Invitation.id == invitation_id,
                Invitation.status == "pending",
            )
            .values(status="cancelled")
            .returning(Invitation)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_expired_bulk(self) -> int:
        """Expire all pending invitations whose expiry has passed. Returns count."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Invitation)
            .where(
                Invitation.status == "pending",
                Invitation.expires_at < now,
            )
            .values(status="expired")
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

"""Invitation model -- tracks user invitations to organizations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from chatcraft_common.database import Base


class Invitation(Base):
    """An invitation for a user to join an organization."""

    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    invited_by = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_invitation_org_email"),
        CheckConstraint(
            "role IN ('admin', 'member')",
            name="chk_invitation_role",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'cancelled')",
            name="chk_invitation_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Invitation email={self.email} org_id={self.organization_id} status={self.status}>"

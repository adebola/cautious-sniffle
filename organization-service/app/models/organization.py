"""OrganizationSettings model -- extended org settings stored locally."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from chatcraft_common.database import Base


class OrganizationSettings(Base):
    """Extended settings for an organization.

    Core organization data (name, slug, status, etc.) lives in the auth service.
    This table stores additional configuration that the organization service owns.
    """

    __tablename__ = "organization_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    timezone = Column(String(50), nullable=False, default="Africa/Lagos")
    default_workspace_template = Column(String(50), nullable=False, default="general")
    allowed_templates = Column(ARRAY(Text), nullable=False, server_default="{}")
    features = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_org_settings_org_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationSettings org_id={self.organization_id}>"

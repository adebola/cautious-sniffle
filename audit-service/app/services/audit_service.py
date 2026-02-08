"""Core audit logging service backed by MongoDB."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import AUDIT_LOGS_COLLECTION
from app.models.audit_log import AuditLogCreate

logger = logging.getLogger(__name__)


class AuditService:
    """Provides audit log persistence and querying against MongoDB."""

    def __init__(self, database: AsyncIOMotorDatabase, default_retention_days: int = 90) -> None:
        self._db = database
        self._collection = database[AUDIT_LOGS_COLLECTION]
        self._default_retention_days = default_retention_days

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def log_event(self, event: AuditLogCreate) -> str:
        """Insert an audit log document and return its ID as a string."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self._default_retention_days)

        document: dict[str, Any] = {
            "organization_id": str(event.organization_id),
            "workspace_id": str(event.workspace_id) if event.workspace_id else None,
            "user_id": str(event.user_id),
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": now,
            "expires_at": expires_at,
        }

        result = await self._collection.insert_one(document)
        log_id = str(result.inserted_id)

        logger.debug(
            "Audit event logged: %s | org=%s | user=%s | id=%s",
            event.action,
            event.organization_id,
            event.user_id,
            log_id,
        )
        return log_id

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def query_logs(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query audit logs with filters and return (items, total_count)."""
        query_filter = self._build_filter(
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
        )

        total_count = await self._collection.count_documents(query_filter)

        skip = (page - 1) * page_size
        cursor = (
            self._collection.find(query_filter)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        documents = await cursor.to_list(length=page_size)

        items = [self._serialize(doc) for doc in documents]
        return items, total_count

    async def get_log(self, log_id: str, organization_id: UUID) -> dict[str, Any] | None:
        """Retrieve a single audit log entry by ID, scoped to an organization."""
        try:
            object_id = ObjectId(log_id)
        except Exception:
            return None

        document = await self._collection.find_one(
            {"_id": object_id, "organization_id": str(organization_id)}
        )
        if document is None:
            return None

        return self._serialize(document)

    async def get_workspace_audit(
        self,
        workspace_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Retrieve audit logs for a specific workspace."""
        query_filter = {
            "organization_id": str(organization_id),
            "workspace_id": str(workspace_id),
        }

        total_count = await self._collection.count_documents(query_filter)

        skip = (page - 1) * page_size
        cursor = (
            self._collection.find(query_filter)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        documents = await cursor.to_list(length=page_size)

        items = [self._serialize(doc) for doc in documents]
        return items, total_count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_filter(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Construct a MongoDB query filter dictionary from optional parameters."""
        query_filter: dict[str, Any] = {
            "organization_id": str(organization_id),
        }

        if workspace_id is not None:
            query_filter["workspace_id"] = str(workspace_id)

        if user_id is not None:
            query_filter["user_id"] = str(user_id)

        if action is not None:
            query_filter["action"] = action

        if resource_type is not None:
            query_filter["resource_type"] = resource_type

        if start_date is not None or end_date is not None:
            date_filter: dict[str, Any] = {}
            if start_date is not None:
                date_filter["$gte"] = start_date
            if end_date is not None:
                date_filter["$lte"] = end_date
            query_filter["created_at"] = date_filter

        return query_filter

    @staticmethod
    def _serialize(document: dict[str, Any]) -> dict[str, Any]:
        """Convert a raw MongoDB document to a serializable dict.

        Replaces ``_id`` (ObjectId) with a string ``id`` field and removes
        internal fields that should not be exposed in API responses.
        """
        serialized = {
            "id": str(document["_id"]),
            "organization_id": document["organization_id"],
            "workspace_id": document.get("workspace_id"),
            "user_id": document["user_id"],
            "action": document["action"],
            "resource_type": document["resource_type"],
            "resource_id": document.get("resource_id"),
            "details": document.get("details", {}),
            "ip_address": document.get("ip_address"),
            "user_agent": document.get("user_agent"),
            "created_at": document["created_at"],
        }
        return serialized

"""MongoDB motor client setup and index management."""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.config import Settings

logger = logging.getLogger(__name__)

AUDIT_LOGS_COLLECTION = "audit_logs"


def create_motor_client(settings: Settings) -> AsyncIOMotorClient:
    """Create and return an async MongoDB client."""
    return AsyncIOMotorClient(settings.mongodb_url)


def get_database(client: AsyncIOMotorClient, settings: Settings) -> AsyncIOMotorDatabase:
    """Return the audit database from the client."""
    return client[settings.mongodb_database]


async def create_indexes(database: AsyncIOMotorDatabase) -> None:
    """Create indexes on the audit_logs collection.

    Called once during application startup.
    """
    collection = database[AUDIT_LOGS_COLLECTION]

    indexes = [
        IndexModel(
            [("organization_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_org_created",
        ),
        IndexModel(
            [("workspace_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_workspace_created",
        ),
        IndexModel(
            [("user_id", ASCENDING)],
            name="idx_user",
        ),
        IndexModel(
            [("action", ASCENDING)],
            name="idx_action",
        ),
        IndexModel(
            [("expires_at", ASCENDING)],
            name="idx_ttl_expires",
            expireAfterSeconds=0,
        ),
    ]

    await collection.create_indexes(indexes)
    logger.info("MongoDB indexes created on '%s' collection", AUDIT_LOGS_COLLECTION)

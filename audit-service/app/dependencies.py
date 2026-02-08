"""FastAPI dependency injection wiring for the Audit Service."""

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from chatcraft_common.auth import CurrentUser, get_current_user  # noqa: F401

from app.services.audit_service import AuditService


def get_database(request: Request) -> AsyncIOMotorDatabase:
    """Return the application-scoped motor database."""
    return request.app.state.database


def get_audit_service(request: Request) -> AuditService:
    """Return the application-scoped AuditService singleton."""
    return request.app.state.audit_service


__all__ = [
    "get_database",
    "get_audit_service",
    "get_current_user",
    "CurrentUser",
]

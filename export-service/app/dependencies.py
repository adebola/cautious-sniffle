"""FastAPI dependency injection wiring for the Export Service."""

from fastapi import Request

from chatcraft_common.auth import CurrentUser, get_current_user  # noqa: F401

from app.services.export_service import ExportService


def get_export_service(request: Request) -> ExportService:
    """Return the application-scoped ExportService singleton."""
    return request.app.state.export_service


__all__ = [
    "get_export_service",
    "get_current_user",
    "CurrentUser",
]

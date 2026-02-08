"""FastAPI dependency injection wiring for the Query Service."""

from fastapi import Request

from chatcraft_common.auth import CurrentUser, get_current_user  # noqa: F401

from app.services.query_processor import QueryProcessor


def get_query_processor(request: Request) -> QueryProcessor:
    """Return the application-scoped QueryProcessor singleton."""
    return request.app.state.query_processor


# Re-export for convenient router imports
__all__ = [
    "get_query_processor",
    "get_current_user",
    "CurrentUser",
]

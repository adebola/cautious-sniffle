"""Standard pagination utilities."""

from typing import Any, Generic, TypeVar

from fastapi import Query as QueryParam
from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams:
    """Dependency for extracting pagination parameters."""

    def __init__(
        self,
        page: int = QueryParam(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = QueryParam(20, ge=1, le=100, description="Items per page"),
        sort_by: str = QueryParam("created_at", description="Field to sort by"),
        sort_order: str = QueryParam("desc", pattern="^(asc|desc)$", description="Sort direction"),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[Any]
    meta: PaginationMeta

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int) -> "PaginatedResponse":
        return cls(
            data=items,
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                has_more=(page * page_size) < total,
            ),
        )

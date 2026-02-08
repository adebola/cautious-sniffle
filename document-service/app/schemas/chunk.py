"""DocumentChunk Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkResponse(BaseModel):
    """Single chunk response."""

    id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    chunk_type: str
    page_number: int | None = None
    section_title: str | None = None
    section_hierarchy: list[str] | None = None
    clause_number: str | None = None
    token_count: int | None = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ChunkSearchRequest(BaseModel):
    """Request body for vector similarity search."""

    query_embedding: list[float]
    document_ids: list[UUID] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class ChunkSearchResult(BaseModel):
    """A single search result with similarity score and parent document info."""

    chunk: ChunkResponse
    similarity: float
    document_title: str | None = None
    document_filename: str

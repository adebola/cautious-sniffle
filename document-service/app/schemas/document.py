"""Document Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Full document response."""

    id: UUID
    organization_id: UUID
    uploaded_by: UUID
    original_filename: str
    file_size: int
    mime_type: str
    title: str | None = None
    description: str | None = None
    document_type: str | None = None
    language: str | None = "en"
    page_count: int | None = None
    classification: dict = Field(default_factory=dict)
    processing_status: str
    processing_error: str | None = None
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    """Fields that can be updated on a document."""

    title: str | None = None
    description: str | None = None
    document_type: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents. Wraps PaginatedResponse."""

    data: list[DocumentResponse]
    meta: dict


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after upload."""

    id: UUID
    original_filename: str
    processing_status: str
    created_at: datetime

    model_config = {"from_attributes": True}

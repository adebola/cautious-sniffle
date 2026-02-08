"""Internal endpoints consumed by other microservices (not routed via Gateway)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_document_service, get_session
from app.schemas.chunk import ChunkSearchRequest
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/documents", tags=["internal"])


# ------------------------------------------------------------------
# Schemas specific to internal endpoints
# ------------------------------------------------------------------


class StatusUpdateRequest(BaseModel):
    """Request body for updating a document's processing status.

    Extended fields (classification, page_count) are set by the ingestion
    service when processing completes successfully.
    """

    status: str
    error: str | None = None
    classification: dict | None = None
    page_count: int | None = None


class BatchGetRequest(BaseModel):
    document_ids: list[UUID]


class ChunkCreateItem(BaseModel):
    """A single chunk received from the ingestion service."""

    content: str
    chunk_index: int
    chunk_type: str = "paragraph"
    page_number: int | None = None
    section_title: str | None = None
    section_hierarchy: list[str] | None = None
    embedding: list[float] | None = None
    token_count: int | None = None
    metadata: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/{document_id}", response_model=dict)
async def get_document_internal(
    document_id: UUID,
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Retrieve a document without organization filtering (internal use only)."""
    result = await service.get_document_internal(session, document_id)
    return {"data": result.model_dump(mode="json")}


@router.get("/{document_id}/status", response_model=dict)
async def get_document_status(
    document_id: UUID,
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Return the current processing status of a document (called by ingestion service)."""
    result = await service.get_document_internal(session, document_id)
    return {
        "data": {
            "document_id": str(result.id),
            "processing_status": result.processing_status,
            "processing_error": result.processing_error,
            "classification": result.classification,
            "page_count": result.page_count,
            "processed_at": result.processed_at.isoformat() if result.processed_at else None,
        }
    }


@router.post("/batch", response_model=dict)
async def batch_get_documents(
    body: BatchGetRequest,
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Retrieve multiple documents by their IDs (internal use only)."""
    results = await service.get_documents_by_ids(session, body.document_ids)
    return {"data": [r.model_dump(mode="json") for r in results]}


@router.put("/{document_id}/status", response_model=dict)
async def update_processing_status(
    document_id: UUID,
    body: StatusUpdateRequest,
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Update the processing status of a document (called by ingestion service).

    When *status* is ``"completed"`` the caller may also supply
    ``classification`` (a JSON-serialisable dict) and ``page_count``.
    """
    updated = await service.update_processing_status(
        session=session,
        document_id=document_id,
        status=body.status,
        error=body.error,
        classification=body.classification,
        page_count=body.page_count,
    )
    return {"data": {"updated": updated}}


@router.post("/{document_id}/chunks", response_model=dict, status_code=201)
async def store_chunks(
    document_id: UUID,
    body: list[ChunkCreateItem],
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Receive and persist document chunks from the ingestion service.

    The ingestion service sends an array of chunk objects (with embeddings)
    after parsing, chunking, and embedding a document.
    """
    count = await service.store_chunks(
        session=session,
        document_id=document_id,
        chunks=[item.model_dump() for item in body],
    )
    logger.info("Stored %d chunks for document %s", count, document_id)
    return {"data": {"stored": count}}


@router.post("/chunks/search", response_model=dict)
async def search_chunks(
    body: ChunkSearchRequest,
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Search document chunks by embedding similarity (called by query service)."""
    results = await service.search_chunks(
        session=session,
        embedding=body.query_embedding,
        document_ids=body.document_ids,
        limit=body.limit,
        threshold=body.threshold,
    )
    return {"data": [r.model_dump(mode="json") for r in results]}

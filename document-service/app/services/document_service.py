"""Core business logic for the Document Service."""

import hashlib
import json
import logging
from uuid import UUID

import aio_pika
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import (
    ChatCraftException,
    ErrorCode,
    LimitExceededException,
    NotFoundException,
)
from chatcraft_common.pagination import PaginatedResponse

from app.config import Settings
from app.models.document import Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.chunk import ChunkResponse, ChunkSearchResult
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DocumentService:
    """Orchestrates document uploads, metadata, storage, and search."""

    def __init__(
        self,
        settings: Settings,
        storage_service: StorageService,
        document_repo: DocumentRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
    ) -> None:
        self._settings = settings
        self._storage = storage_service
        self._doc_repo = document_repo or DocumentRepository()
        self._chunk_repo = chunk_repo or ChunkRepository()

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    async def upload_document(
        self,
        session: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        file: UploadFile,
        title: str | None = None,
        description: str | None = None,
    ) -> DocumentUploadResponse:
        """Validate, store, persist, and enqueue a new document upload."""

        # 1. Validate MIME type
        if file.content_type not in self._settings.allowed_mime_types:
            raise ChatCraftException(
                status_code=400,
                code=ErrorCode.DOC_UNSUPPORTED_TYPE,
                message=f"Unsupported file type: {file.content_type}. "
                f"Allowed: {', '.join(self._settings.allowed_mime_types)}",
            )

        # 2. Read and validate size
        file_data = await file.read()
        if len(file_data) > self._settings.max_file_size_bytes:
            raise LimitExceededException(
                code=ErrorCode.DOC_SIZE_EXCEEDED,
                message=f"File exceeds maximum size of {self._settings.max_file_size_mb} MB",
                details={"max_bytes": self._settings.max_file_size_bytes, "actual_bytes": len(file_data)},
            )

        # 3. Compute SHA-256 hash
        file_hash = hashlib.sha256(file_data).hexdigest()

        # 4. Upload to object storage
        storage_path = await self._storage.upload_file(
            organization_id=str(organization_id),
            file_name=file.filename or "untitled",
            file_data=file_data,
            content_type=file.content_type or "application/octet-stream",
        )

        # 5. Create database record
        document = Document(
            organization_id=organization_id,
            uploaded_by=user_id,
            original_filename=file.filename or "untitled",
            storage_path=storage_path,
            file_size=len(file_data),
            mime_type=file.content_type or "application/octet-stream",
            file_hash=file_hash,
            title=title or file.filename,
            description=description,
            processing_status="pending",
        )
        document = await self._doc_repo.create(session, document)

        # 6. Publish processing event (best-effort; do not block upload)
        try:
            await self._publish_process_event(
                document_id=document.id,
                organization_id=organization_id,
                storage_path=storage_path,
            )
        except Exception:
            logger.exception("Failed to publish process event for document %s", document.id)

        return DocumentUploadResponse.model_validate(document)

    # ------------------------------------------------------------------
    # Batch Upload
    # ------------------------------------------------------------------

    async def upload_documents_batch(
        self,
        session: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        files: list[UploadFile],
        title: str | None = None,
        description: str | None = None,
    ) -> list[DocumentUploadResponse]:
        """Upload multiple documents in a single request."""
        results: list[DocumentUploadResponse] = []
        for file in files:
            response = await self.upload_document(
                session=session,
                organization_id=organization_id,
                user_id=user_id,
                file=file,
                title=title,
                description=description,
            )
            results.append(response)
        return results

    # ------------------------------------------------------------------
    # List / Get / Update / Delete
    # ------------------------------------------------------------------

    async def list_documents(
        self,
        session: AsyncSession,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedResponse:
        """Return a paginated list of documents for an organization."""
        documents, total = await self._doc_repo.list_by_org(
            session,
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [DocumentResponse.model_validate(d) for d in documents]
        return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)

    async def get_document(
        self,
        session: AsyncSession,
        organization_id: UUID,
        document_id: UUID,
    ) -> DocumentResponse:
        """Retrieve a single document, scoped to the caller's organization."""
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )
        return DocumentResponse.model_validate(doc)

    async def get_document_internal(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> DocumentResponse:
        """Retrieve a document without org filtering (for internal calls)."""
        doc = await self._doc_repo.get_by_id(session, document_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )
        return DocumentResponse.model_validate(doc)

    async def update_document(
        self,
        session: AsyncSession,
        organization_id: UUID,
        document_id: UUID,
        title: str | None = None,
        description: str | None = None,
        document_type: str | None = None,
    ) -> DocumentResponse:
        """Update editable metadata on a document."""
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )
        if title is not None:
            doc.title = title
        if description is not None:
            doc.description = description
        if document_type is not None:
            doc.document_type = document_type

        doc = await self._doc_repo.update(session, doc)
        return DocumentResponse.model_validate(doc)

    async def delete_document(
        self,
        session: AsyncSession,
        organization_id: UUID,
        document_id: UUID,
    ) -> bool:
        """Soft-delete a document and remove the file from object storage."""
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )

        deleted = await self._doc_repo.soft_delete(session, document_id, organization_id)
        if deleted:
            # Best-effort cleanup of the stored file
            try:
                await self._storage.delete_file(doc.storage_path)
            except Exception:
                logger.exception("Failed to delete stored file %s", doc.storage_path)
        return deleted

    async def get_download_url(
        self,
        session: AsyncSession,
        organization_id: UUID,
        document_id: UUID,
    ) -> str:
        """Return a presigned download URL for a document."""
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )
        return await self._storage.get_presigned_url(doc.storage_path)

    # ------------------------------------------------------------------
    # Reprocessing
    # ------------------------------------------------------------------

    async def reprocess_document(
        self,
        session: AsyncSession,
        organization_id: UUID,
        document_id: UUID,
    ) -> DocumentResponse:
        """Reset status to pending and re-publish the processing event."""
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        if not doc:
            raise NotFoundException(
                code=ErrorCode.DOC_NOT_FOUND,
                message=f"Document {document_id} not found",
            )

        await self._doc_repo.update_processing_status(session, document_id, "pending")

        try:
            await self._publish_process_event(
                document_id=document_id,
                organization_id=organization_id,
                storage_path=doc.storage_path,
            )
        except Exception:
            logger.exception("Failed to publish reprocess event for document %s", document_id)

        # Re-fetch to return updated status
        doc = await self._doc_repo.get_by_id(session, document_id, organization_id)
        return DocumentResponse.model_validate(doc)

    # ------------------------------------------------------------------
    # Processing status (called by ingestion service)
    # ------------------------------------------------------------------

    async def update_processing_status(
        self,
        session: AsyncSession,
        document_id: UUID,
        status: str,
        error: str | None = None,
        classification: dict | None = None,
        page_count: int | None = None,
    ) -> bool:
        """Update processing status from an internal caller.

        When *status* is ``"completed"`` the caller may also supply
        ``classification`` (JSON metadata) and ``page_count``.
        """
        return await self._doc_repo.update_processing_status(
            session,
            document_id,
            status,
            error=error,
            classification=classification,
            page_count=page_count,
        )

    # ------------------------------------------------------------------
    # Chunk storage (called by ingestion service)
    # ------------------------------------------------------------------

    async def store_chunks(
        self,
        session: AsyncSession,
        document_id: UUID,
        chunks: list[dict],
    ) -> int:
        """Persist a batch of document chunks received from the ingestion service.

        Before inserting the new chunks, any existing chunks for the document
        are deleted so that re-processing is idempotent.

        Args:
            session: Active database session.
            document_id: The document these chunks belong to.
            chunks: List of chunk dicts as sent by the ingestion service.

        Returns:
            The number of chunks stored.
        """
        from app.models.chunk import DocumentChunk

        # Delete existing chunks (idempotent re-processing)
        await self._chunk_repo.delete_by_document(session, document_id)

        chunk_models = [
            DocumentChunk(
                document_id=document_id,
                content=c["content"],
                chunk_index=c["chunk_index"],
                chunk_type=c.get("chunk_type", "paragraph"),
                page_number=c.get("page_number"),
                section_title=c.get("section_title"),
                section_hierarchy=c.get("section_hierarchy"),
                embedding=c.get("embedding"),
                token_count=c.get("token_count"),
                metadata_=c.get("metadata", {}),
            )
            for c in chunks
        ]

        stored = await self._chunk_repo.create_batch(session, chunk_models)
        logger.info("Stored %d chunks for document %s", len(stored), document_id)
        return len(stored)

    # ------------------------------------------------------------------
    # Chunk search
    # ------------------------------------------------------------------

    async def search_chunks(
        self,
        session: AsyncSession,
        embedding: list[float],
        document_ids: list[UUID],
        limit: int = 10,
        threshold: float = 0.3,
    ) -> list[ChunkSearchResult]:
        """Perform cosine similarity search over document chunks."""
        results = await self._chunk_repo.search_by_embedding(
            session,
            embedding=embedding,
            document_ids=document_ids,
            limit=limit,
            threshold=threshold,
        )

        search_results: list[ChunkSearchResult] = []
        for chunk, similarity in results:
            # Eagerly load parent document info for the result payload
            doc = await self._doc_repo.get_by_id(session, chunk.document_id)
            chunk_resp = ChunkResponse.model_validate(chunk)
            search_results.append(
                ChunkSearchResult(
                    chunk=chunk_resp,
                    similarity=round(similarity, 6),
                    document_title=doc.title if doc else None,
                    document_filename=doc.original_filename if doc else "unknown",
                )
            )
        return search_results

    # ------------------------------------------------------------------
    # Batch get (internal)
    # ------------------------------------------------------------------

    async def get_documents_by_ids(
        self,
        session: AsyncSession,
        document_ids: list[UUID],
    ) -> list[DocumentResponse]:
        """Return documents matching the given IDs (no org filter)."""
        results: list[DocumentResponse] = []
        for doc_id in document_ids:
            doc = await self._doc_repo.get_by_id(session, doc_id)
            if doc:
                results.append(DocumentResponse.model_validate(doc))
        return results

    # ------------------------------------------------------------------
    # RabbitMQ publishing
    # ------------------------------------------------------------------

    async def _publish_process_event(
        self,
        document_id: UUID,
        organization_id: UUID,
        storage_path: str,
    ) -> None:
        """Publish a ``document.process`` event to RabbitMQ."""
        connection = await aio_pika.connect_robust(self._settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                "chatcraft",
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            body = json.dumps(
                {
                    "document_id": str(document_id),
                    "organization_id": str(organization_id),
                    "storage_path": storage_path,
                }
            ).encode()
            message = aio_pika.Message(
                body=body,
                content_type="application/json",
            )
            await exchange.publish(message, routing_key="document.process")
            logger.info("Published document.process for %s", document_id)

"""Repository for Document CRUD operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    """Data-access layer for the documents table."""

    async def create(self, session: AsyncSession, document: Document) -> Document:
        """Insert a new document record."""
        session.add(document)
        await session.flush()
        await session.refresh(document)
        return document

    async def get_by_id(
        self,
        session: AsyncSession,
        document_id: UUID,
        organization_id: UUID | None = None,
    ) -> Document | None:
        """Fetch a document by ID, optionally scoped to an organization.

        Soft-deleted documents are excluded.
        """
        stmt = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
        if organization_id is not None:
            stmt = stmt.where(Document.organization_id == organization_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        session: AsyncSession,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Document], int]:
        """List documents for an organization with filtering, search, and pagination.

        Returns a tuple of (documents, total_count).
        """
        base = select(Document).where(
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )

        if status:
            base = base.where(Document.processing_status == status)

        if search:
            search_filter = f"%{search}%"
            base = base.where(
                Document.original_filename.ilike(search_filter)
                | Document.title.ilike(search_filter)
                | Document.description.ilike(search_filter)
            )

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        allowed_sort_columns = {
            "created_at": Document.created_at,
            "updated_at": Document.updated_at,
            "original_filename": Document.original_filename,
            "file_size": Document.file_size,
            "title": Document.title,
            "processing_status": Document.processing_status,
        }
        sort_column = allowed_sort_columns.get(sort_by, Document.created_at)
        if sort_order == "asc":
            base = base.order_by(sort_column.asc())
        else:
            base = base.order_by(sort_column.desc())

        # Pagination
        offset = (page - 1) * page_size
        base = base.offset(offset).limit(page_size)

        result = await session.execute(base)
        documents = list(result.scalars().all())
        return documents, total

    async def update(self, session: AsyncSession, document: Document) -> Document:
        """Persist changes on a managed Document instance."""
        await session.flush()
        await session.refresh(document)
        return document

    async def soft_delete(
        self,
        session: AsyncSession,
        document_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """Mark a document as deleted (soft delete)."""
        stmt = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.organization_id == organization_id,
                Document.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    async def update_processing_status(
        self,
        session: AsyncSession,
        document_id: UUID,
        status: str,
        error: str | None = None,
        classification: dict | None = None,
        page_count: int | None = None,
    ) -> bool:
        """Update the processing status of a document.

        When *status* is ``"completed"`` the caller may also supply
        ``classification`` (JSON metadata) and ``page_count``.
        """
        values: dict = {"processing_status": status}
        if error is not None:
            values["processing_error"] = error
        if classification is not None:
            values["classification"] = classification
        if page_count is not None:
            values["page_count"] = page_count
        if status == "completed":
            values["processed_at"] = datetime.now(timezone.utc)
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(**values)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    async def count_by_org(self, session: AsyncSession, organization_id: UUID) -> int:
        """Return the total number of (non-deleted) documents for an org."""
        stmt = select(func.count()).where(
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

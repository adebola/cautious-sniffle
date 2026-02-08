"""Repository for DocumentChunk CRUD and vector search operations."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk


class ChunkRepository:
    """Data-access layer for the document_chunks table."""

    async def create_batch(
        self,
        session: AsyncSession,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        """Insert a batch of chunks in a single flush."""
        session.add_all(chunks)
        await session.flush()
        for chunk in chunks:
            await session.refresh(chunk)
        return chunks

    async def get_by_document(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        """Return all chunks belonging to a document, ordered by index."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_embedding(
        self,
        session: AsyncSession,
        embedding: list[float],
        document_ids: list[UUID],
        limit: int = 10,
        threshold: float = 0.3,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search chunks by cosine similarity to the given embedding vector.

        Returns a list of (chunk, similarity_score) tuples ordered by
        descending similarity, filtered to only include results above the
        threshold.
        """
        similarity = 1 - DocumentChunk.embedding.cosine_distance(embedding)
        similarity_label = similarity.label("similarity")

        stmt = select(DocumentChunk, similarity_label).where(
            DocumentChunk.embedding.is_not(None),
            similarity >= threshold,
        )

        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

        stmt = stmt.order_by(similarity_label.desc()).limit(limit)

        result = await session.execute(stmt)
        rows = result.all()
        return [(row[0], float(row[1])) for row in rows]

    async def delete_by_document(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> int:
        """Delete all chunks for a document. Returns the number deleted."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

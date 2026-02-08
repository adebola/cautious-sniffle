"""Main document ingestion pipeline.

Coordinates the full lifecycle of document processing:
  1. Status update -> "processing"
  2. Download from MinIO
  3. Parse into structured sections
  4. Chunk sections into token-bounded pieces
  5. Generate vector embeddings
  6. Classify the document via LLM
  7. Store chunks + embeddings via Document Service internal API
  8. Status update -> "completed" (or "failed")
"""

import logging
import os

from chatcraft_common.clients import ServiceClient

from app.chunking.smart_chunker import SmartChunker
from app.classification.classifier import DocumentClassifier
from app.config import Settings
from app.embedding.embedding_service import EmbeddingService
from app.parsers.base import BaseParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.text_parser import TextParser
from app.parsers.xlsx_parser import XlsxParser
from app.services.storage_client import StorageClient

logger = logging.getLogger(__name__)

# File extension -> parser mapping
_EXTENSION_PARSER_MAP: dict[str, type[BaseParser]] = {
    ".pdf": PdfParser,
    ".docx": DocxParser,
    ".xlsx": XlsxParser,
    ".txt": TextParser,
    ".csv": TextParser,
    ".md": TextParser,
    ".text": TextParser,
}


class IngestionPipeline:
    """Orchestrates the full document ingestion flow.

    Constructed once and reused for every message consumed from RabbitMQ.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        # Storage (MinIO)
        self.storage = StorageClient(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )

        # Document Service internal client
        self.doc_client = ServiceClient(
            base_url=settings.document_service_url,
            timeout=30.0,
        )

        # Chunker
        self.chunker = SmartChunker(
            max_tokens=settings.chunk_size,
            overlap_tokens=settings.chunk_overlap,
        )

        # Embedding service
        self.embedding_service = EmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )

        # Classifier
        self.classifier = DocumentClassifier(
            api_key=settings.openai_api_key,
            model=settings.default_llm_model,
        )

    async def process_document(
        self,
        document_id: str,
        organization_id: str,
        storage_path: str,
    ) -> None:
        """Run the full ingestion pipeline for a single document.

        Args:
            document_id: UUID of the document record.
            organization_id: UUID of the owning organisation.
            storage_path: Object key in MinIO where the file is stored.
        """
        file_path: str | None = None

        try:
            # ----------------------------------------------------------
            # 1. Mark document as "processing"
            # ----------------------------------------------------------
            logger.info(
                "Starting ingestion for document %s (org %s)",
                document_id,
                organization_id,
            )
            await self.doc_client.put(
                f"/internal/documents/{document_id}/status",
                json={"status": "processing"},
            )

            # ----------------------------------------------------------
            # 2. Download file from MinIO
            # ----------------------------------------------------------
            file_path = await self.storage.download_file(storage_path)
            logger.info("Downloaded %s -> %s", storage_path, file_path)

            # ----------------------------------------------------------
            # 3. Select parser based on file extension
            # ----------------------------------------------------------
            parser = self._get_parser(storage_path)
            logger.info("Using parser: %s", type(parser).__name__)

            # ----------------------------------------------------------
            # 4. Parse document into sections
            # ----------------------------------------------------------
            sections = await parser.parse(file_path)
            logger.info("Parsed %d sections", len(sections))

            if not sections:
                logger.warning("No sections extracted from document %s", document_id)
                await self.doc_client.put(
                    f"/internal/documents/{document_id}/status",
                    json={
                        "status": "completed",
                        "classification": {
                            "detected_type": "other",
                            "confidence": 0.0,
                            "structure": {
                                "has_toc": False,
                                "section_count": 0,
                                "has_tables": False,
                            },
                            "entities": [],
                            "dates_mentioned": [],
                        },
                        "page_count": 0,
                    },
                )
                return

            # ----------------------------------------------------------
            # 5. Chunk sections
            # ----------------------------------------------------------
            chunks = self.chunker.chunk_sections(sections)
            logger.info("Produced %d chunks", len(chunks))

            # ----------------------------------------------------------
            # 6. Generate embeddings for all chunks
            # ----------------------------------------------------------
            texts = [c.content for c in chunks]
            embeddings = await self.embedding_service.generate_embeddings(texts)
            logger.info("Generated %d embeddings", len(embeddings))

            # ----------------------------------------------------------
            # 7. Classify document using initial text
            # ----------------------------------------------------------
            sample_text = " ".join(texts[:5])[:4000]
            classification = await self.classifier.classify_document(sample_text)
            logger.info(
                "Document classified as %s (confidence %.2f)",
                classification.get("detected_type"),
                classification.get("confidence", 0),
            )

            # ----------------------------------------------------------
            # 8. Store chunks via Document Service internal API
            # ----------------------------------------------------------
            chunk_payload = [
                {
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "section_hierarchy": chunk.section_hierarchy,
                    "embedding": embedding,
                    "token_count": chunk.token_count,
                    "metadata": {},
                }
                for chunk, embedding in zip(chunks, embeddings)
            ]

            await self.doc_client.post(
                f"/internal/documents/{document_id}/chunks",
                json=chunk_payload,
            )
            logger.info(
                "Stored %d chunks for document %s",
                len(chunk_payload),
                document_id,
            )

            # ----------------------------------------------------------
            # 9. Update document status to completed
            # ----------------------------------------------------------
            page_count = max(
                (s.page_number or 0 for s in sections),
                default=0,
            )
            await self.doc_client.put(
                f"/internal/documents/{document_id}/status",
                json={
                    "status": "completed",
                    "classification": classification,
                    "page_count": page_count,
                },
            )
            logger.info("Document %s processing completed", document_id)

        except Exception as exc:
            logger.error(
                "Failed to process document %s: %s",
                document_id,
                exc,
                exc_info=True,
            )
            try:
                await self.doc_client.put(
                    f"/internal/documents/{document_id}/status",
                    json={
                        "status": "failed",
                        "error": str(exc),
                    },
                )
            except Exception:
                logger.exception(
                    "Failed to update document %s status to 'failed'",
                    document_id,
                )

        finally:
            if file_path:
                self.storage.cleanup_temp(file_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_parser(storage_path: str) -> BaseParser:
        """Select the appropriate parser based on the file extension."""
        _, ext = os.path.splitext(storage_path)
        ext = ext.lower()

        parser_cls = _EXTENSION_PARSER_MAP.get(ext)
        if parser_cls is None:
            raise ValueError(
                f"Unsupported file extension '{ext}' for path: {storage_path}"
            )

        return parser_cls()

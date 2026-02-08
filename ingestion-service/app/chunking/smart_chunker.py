"""Token-aware smart chunker that respects sentence boundaries."""

import logging
import re
from dataclasses import dataclass, field

import tiktoken

from app.parsers.base import ParsedSection

logger = logging.getLogger(__name__)

# Sentence-ending patterns (handles ". ", "? ", "! ", and newline terminators)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|(?<=\n)")


@dataclass
class ChunkData:
    """A single chunk produced by the smart chunker.

    Attributes:
        content: The text content of the chunk.
        chunk_index: Zero-based global index across all chunks of a document.
        chunk_type: Semantic type inherited from the source section.
        page_number: Page number from the source section (may be None).
        section_title: Section title from the source section.
        section_hierarchy: Section hierarchy from the source section.
        clause_number: Optional clause / article number if detected.
        token_count: Number of tokens in this chunk.
    """

    content: str
    chunk_index: int
    chunk_type: str = "paragraph"
    page_number: int | None = None
    section_title: str | None = None
    section_hierarchy: list[str] | None = field(default_factory=list)
    clause_number: str | None = None
    token_count: int = 0


class SmartChunker:
    """Splits parsed sections into token-bounded chunks.

    Uses tiktoken with the ``cl100k_base`` encoding (used by text-embedding-3-small
    and GPT-4 family models) to count tokens accurately.

    Algorithm:
        1. Iterate over sections.
        2. If a section fits within ``max_tokens``, emit it as a single chunk.
        3. If it exceeds ``max_tokens``, split at sentence boundaries so that each
           sub-chunk stays within budget.
        4. Maintain overlap by prepending ``overlap_tokens`` worth of text from the
           end of the previous chunk to the beginning of the next.
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Return the number of tokens in *text*."""
        return len(self._enc.encode(text))

    def chunk_sections(
        self,
        sections: list[ParsedSection],
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
    ) -> list[ChunkData]:
        """Split *sections* into chunks respecting the token budget.

        Args:
            sections: Output from a document parser.
            max_tokens: Override for ``self.max_tokens``.
            overlap_tokens: Override for ``self.overlap_tokens``.

        Returns:
            An ordered list of ``ChunkData`` objects.
        """
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        overlap_tok = overlap_tokens if overlap_tokens is not None else self.overlap_tokens

        chunks: list[ChunkData] = []
        chunk_index = 0
        previous_overlap_text = ""

        for section in sections:
            text = section.content.strip()
            if not text:
                continue

            token_count = self.count_tokens(text)

            if token_count <= max_tok:
                # Section fits in one chunk - prepend overlap from previous chunk
                final_text = self._prepend_overlap(previous_overlap_text, text, max_tok)
                final_token_count = self.count_tokens(final_text)

                chunks.append(
                    ChunkData(
                        content=final_text,
                        chunk_index=chunk_index,
                        chunk_type=section.chunk_type,
                        page_number=section.page_number,
                        section_title=section.section_title,
                        section_hierarchy=section.section_hierarchy or [],
                        clause_number=self._detect_clause(text),
                        token_count=final_token_count,
                    )
                )
                previous_overlap_text = self._tail_tokens(text, overlap_tok)
                chunk_index += 1
            else:
                # Section is too large - split at sentence boundaries
                sentences = _SENTENCE_SPLIT_RE.split(text)
                sentences = [s.strip() for s in sentences if s.strip()]

                current_parts: list[str] = []
                current_tok = 0

                for sentence in sentences:
                    sent_tok = self.count_tokens(sentence)

                    if sent_tok > max_tok:
                        # Single sentence exceeds budget - force-split by tokens
                        if current_parts:
                            chunk_text = " ".join(current_parts)
                            final_text = self._prepend_overlap(previous_overlap_text, chunk_text, max_tok)
                            final_tok = self.count_tokens(final_text)
                            chunks.append(
                                ChunkData(
                                    content=final_text,
                                    chunk_index=chunk_index,
                                    chunk_type=section.chunk_type,
                                    page_number=section.page_number,
                                    section_title=section.section_title,
                                    section_hierarchy=section.section_hierarchy or [],
                                    clause_number=self._detect_clause(chunk_text),
                                    token_count=final_tok,
                                )
                            )
                            previous_overlap_text = self._tail_tokens(chunk_text, overlap_tok)
                            chunk_index += 1
                            current_parts = []
                            current_tok = 0

                        # Force-split the oversized sentence
                        sub_chunks = self._force_split(sentence, max_tok, overlap_tok)
                        for sc in sub_chunks:
                            final_text = self._prepend_overlap(previous_overlap_text, sc, max_tok)
                            final_tok = self.count_tokens(final_text)
                            chunks.append(
                                ChunkData(
                                    content=final_text,
                                    chunk_index=chunk_index,
                                    chunk_type=section.chunk_type,
                                    page_number=section.page_number,
                                    section_title=section.section_title,
                                    section_hierarchy=section.section_hierarchy or [],
                                    clause_number=self._detect_clause(sc),
                                    token_count=final_tok,
                                )
                            )
                            previous_overlap_text = self._tail_tokens(sc, overlap_tok)
                            chunk_index += 1
                        continue

                    if current_tok + sent_tok > max_tok and current_parts:
                        # Flush current accumulator
                        chunk_text = " ".join(current_parts)
                        final_text = self._prepend_overlap(previous_overlap_text, chunk_text, max_tok)
                        final_tok = self.count_tokens(final_text)
                        chunks.append(
                            ChunkData(
                                content=final_text,
                                chunk_index=chunk_index,
                                chunk_type=section.chunk_type,
                                page_number=section.page_number,
                                section_title=section.section_title,
                                section_hierarchy=section.section_hierarchy or [],
                                clause_number=self._detect_clause(chunk_text),
                                token_count=final_tok,
                            )
                        )
                        previous_overlap_text = self._tail_tokens(chunk_text, overlap_tok)
                        chunk_index += 1
                        current_parts = []
                        current_tok = 0

                    current_parts.append(sentence)
                    current_tok += sent_tok

                # Flush remaining sentences
                if current_parts:
                    chunk_text = " ".join(current_parts)
                    final_text = self._prepend_overlap(previous_overlap_text, chunk_text, max_tok)
                    final_tok = self.count_tokens(final_text)
                    chunks.append(
                        ChunkData(
                            content=final_text,
                            chunk_index=chunk_index,
                            chunk_type=section.chunk_type,
                            page_number=section.page_number,
                            section_title=section.section_title,
                            section_hierarchy=section.section_hierarchy or [],
                            clause_number=self._detect_clause(chunk_text),
                            token_count=final_tok,
                        )
                    )
                    previous_overlap_text = self._tail_tokens(chunk_text, overlap_tok)
                    chunk_index += 1

        logger.info("Chunking complete: %d chunks produced", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prepend_overlap(self, overlap_text: str, text: str, max_tok: int) -> str:
        """Prepend overlap text if it fits within the budget."""
        if not overlap_text:
            return text
        combined = overlap_text + " " + text
        if self.count_tokens(combined) <= max_tok:
            return combined
        # If combined exceeds budget, skip the overlap to stay within limits
        return text

    def _tail_tokens(self, text: str, n_tokens: int) -> str:
        """Return the last *n_tokens* worth of text."""
        tokens = self._enc.encode(text)
        if len(tokens) <= n_tokens:
            return text
        return self._enc.decode(tokens[-n_tokens:])

    def _force_split(self, text: str, max_tok: int, overlap_tok: int) -> list[str]:
        """Split text into chunks of at most *max_tok* tokens by brute token slicing."""
        tokens = self._enc.encode(text)
        parts: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + max_tok, len(tokens))
            parts.append(self._enc.decode(tokens[start:end]))
            start = end - overlap_tok if end < len(tokens) else end
        return parts

    @staticmethod
    def _detect_clause(text: str) -> str | None:
        """Attempt to detect a clause / article number at the start of the text."""
        match = re.match(
            r"^(?:(?:Article|Section|Clause|Part)\s+)?(\d+(?:\.\d+)*)",
            text.strip(),
            re.IGNORECASE,
        )
        return match.group(0).strip() if match else None

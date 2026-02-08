"""PDF parser using PyMuPDF (fitz)."""

import logging

import fitz  # PyMuPDF

from app.parsers.base import BaseParser, ParsedSection

logger = logging.getLogger(__name__)

# Heuristic thresholds for heading detection
_HEADING_FONT_SIZE_RATIO = 1.15  # 15% larger than median font size
_HEADING_MIN_LENGTH = 3
_HEADING_MAX_LENGTH = 200


class PdfParser(BaseParser):
    """Extracts structured sections from PDF documents.

    Uses PyMuPDF to iterate over each page, extracting text blocks with font
    metadata.  Bold or larger-font spans are treated as headings; contiguous
    body text is grouped into paragraph sections.
    """

    async def parse(self, file_path: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []

        try:
            doc = fitz.open(file_path)
        except Exception:
            logger.exception("Failed to open PDF: %s", file_path)
            raise

        try:
            median_size = self._compute_median_font_size(doc)
            heading_threshold = median_size * _HEADING_FONT_SIZE_RATIO if median_size else 14.0

            current_hierarchy: list[str] = []
            current_section_title: str | None = None
            current_text_parts: list[str] = []
            current_page: int | None = None

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_number = page_idx + 1
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

                for block in blocks:
                    if block.get("type") != 0:
                        # Skip image blocks
                        continue

                    for line in block.get("lines", []):
                        line_text = ""
                        is_heading = False

                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if not span_text:
                                continue
                            line_text += span_text + " "

                            font_size = span.get("size", 12.0)
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & 2**4)  # bit 4 = bold

                            if (font_size >= heading_threshold or is_bold) and len(span_text) <= _HEADING_MAX_LENGTH:
                                is_heading = True

                        line_text = line_text.strip()
                        if not line_text or len(line_text) < _HEADING_MIN_LENGTH:
                            continue

                        if is_heading and len(line_text) <= _HEADING_MAX_LENGTH:
                            # Flush accumulated paragraph text
                            if current_text_parts:
                                sections.append(
                                    ParsedSection(
                                        content="\n".join(current_text_parts).strip(),
                                        page_number=current_page,
                                        section_title=current_section_title,
                                        section_hierarchy=list(current_hierarchy),
                                        chunk_type="paragraph",
                                    )
                                )
                                current_text_parts = []

                            # Update heading tracking
                            current_section_title = line_text
                            current_hierarchy = current_hierarchy[:0]  # reset
                            current_hierarchy.append(line_text)
                            current_page = page_number

                            # Also emit the heading itself as a section
                            sections.append(
                                ParsedSection(
                                    content=line_text,
                                    page_number=page_number,
                                    section_title=line_text,
                                    section_hierarchy=list(current_hierarchy),
                                    chunk_type="heading",
                                )
                            )
                        else:
                            current_text_parts.append(line_text)
                            if current_page is None:
                                current_page = page_number

            # Flush remaining text
            if current_text_parts:
                sections.append(
                    ParsedSection(
                        content="\n".join(current_text_parts).strip(),
                        page_number=current_page,
                        section_title=current_section_title,
                        section_hierarchy=list(current_hierarchy),
                        chunk_type="paragraph",
                    )
                )
        finally:
            doc.close()

        # If no sections were extracted (e.g. scanned PDF with no text layer),
        # fall back to raw per-page text extraction.
        if not sections:
            sections = self._fallback_per_page(file_path)

        logger.info("PDF parsed: %d sections from %s", len(sections), file_path)
        return sections

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_median_font_size(doc: fitz.Document) -> float:
        """Sample font sizes across the document and return the median."""
        sizes: list[float] = []
        max_pages_to_sample = min(len(doc), 10)
        for page_idx in range(max_pages_to_sample):
            page = doc[page_idx]
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            sizes.append(span.get("size", 12.0))

        if not sizes:
            return 12.0

        sizes.sort()
        mid = len(sizes) // 2
        if len(sizes) % 2 == 0:
            return (sizes[mid - 1] + sizes[mid]) / 2.0
        return sizes[mid]

    @staticmethod
    def _fallback_per_page(file_path: str) -> list[ParsedSection]:
        """Fallback: extract raw text per page when structured extraction yields nothing."""
        sections: list[ParsedSection] = []
        doc = fitz.open(file_path)
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text("text").strip()
                if text:
                    sections.append(
                        ParsedSection(
                            content=text,
                            page_number=page_idx + 1,
                            section_title=None,
                            section_hierarchy=[],
                            chunk_type="paragraph",
                        )
                    )
        finally:
            doc.close()
        return sections

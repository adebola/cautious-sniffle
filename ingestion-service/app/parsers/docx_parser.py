"""DOCX parser using python-docx."""

import logging

from docx import Document as DocxDocument
from docx.table import Table

from app.parsers.base import BaseParser, ParsedSection

logger = logging.getLogger(__name__)

# Mapping of python-docx heading style prefixes to hierarchy depth
_HEADING_DEPTH_MAP = {
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "Heading 4": 4,
    "Heading 5": 5,
    "Heading 6": 6,
    "Title": 0,
    "Subtitle": 0,
}


class DocxParser(BaseParser):
    """Extracts structured sections from DOCX documents.

    Iterates over paragraphs and tables in document order.  Heading-style
    paragraphs are used to establish section hierarchy; body paragraphs are
    grouped under their nearest heading.  Tables are serialised to a
    pipe-delimited text representation.
    """

    async def parse(self, file_path: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []

        try:
            doc = DocxDocument(file_path)
        except Exception:
            logger.exception("Failed to open DOCX: %s", file_path)
            raise

        # Track section hierarchy as a stack of (depth, title) tuples
        hierarchy_stack: list[tuple[int, str]] = []
        current_section_title: str | None = None
        current_text_parts: list[str] = []

        def _flush() -> None:
            """Emit the accumulated paragraph text as a section."""
            nonlocal current_text_parts
            if current_text_parts:
                combined = "\n".join(current_text_parts).strip()
                if combined:
                    sections.append(
                        ParsedSection(
                            content=combined,
                            page_number=None,  # DOCX does not expose page numbers easily
                            section_title=current_section_title,
                            section_hierarchy=[title for _, title in hierarchy_stack],
                            chunk_type="paragraph",
                        )
                    )
                current_text_parts = []

        # Iterate over all block-level elements (paragraphs and tables) in order.
        for element in doc.element.body:
            tag = element.tag.split("}")[-1]  # strip namespace

            if tag == "p":
                paragraph = self._element_to_paragraph(doc, element)
                if paragraph is None:
                    continue

                text = paragraph.text.strip()
                if not text:
                    continue

                style_name = paragraph.style.name if paragraph.style else ""

                heading_depth = self._heading_depth(style_name)
                if heading_depth is not None:
                    # Flush previous body text
                    _flush()

                    # Update hierarchy stack: pop anything at same or deeper depth
                    while hierarchy_stack and hierarchy_stack[-1][0] >= heading_depth:
                        hierarchy_stack.pop()
                    hierarchy_stack.append((heading_depth, text))

                    current_section_title = text

                    sections.append(
                        ParsedSection(
                            content=text,
                            page_number=None,
                            section_title=text,
                            section_hierarchy=[title for _, title in hierarchy_stack],
                            chunk_type="heading",
                        )
                    )
                else:
                    current_text_parts.append(text)

            elif tag == "tbl":
                # Flush any body text before the table
                _flush()

                table = self._element_to_table(doc, element)
                if table is not None:
                    table_text = self._table_to_text(table)
                    if table_text:
                        sections.append(
                            ParsedSection(
                                content=table_text,
                                page_number=None,
                                section_title=current_section_title,
                                section_hierarchy=[title for _, title in hierarchy_stack],
                                chunk_type="table",
                            )
                        )

        # Flush remaining text
        _flush()

        logger.info("DOCX parsed: %d sections from %s", len(sections), file_path)
        return sections

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _heading_depth(style_name: str) -> int | None:
        """Return the heading depth for a style name, or None if not a heading."""
        for prefix, depth in _HEADING_DEPTH_MAP.items():
            if style_name.startswith(prefix):
                return depth
        return None

    @staticmethod
    def _element_to_paragraph(doc: DocxDocument, element):
        """Convert an lxml paragraph element back to a python-docx Paragraph, or None."""
        from docx.text.paragraph import Paragraph

        try:
            return Paragraph(element, doc)
        except Exception:
            return None

    @staticmethod
    def _element_to_table(doc: DocxDocument, element) -> Table | None:
        """Convert an lxml table element back to a python-docx Table, or None."""
        try:
            return Table(element, doc)
        except Exception:
            return None

    @staticmethod
    def _table_to_text(table: Table) -> str:
        """Serialise a python-docx Table to a pipe-delimited text representation."""
        rows_text: list[str] = []
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows_text.append(" | ".join(cells))
        return "\n".join(rows_text)

"""Plain-text and CSV parser."""

import logging
import re

from app.parsers.base import BaseParser, ParsedSection

logger = logging.getLogger(__name__)

# Patterns for heuristic heading detection in plain text
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z\s\-:]{2,80}$")
_NUMBERED_SECTION_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\s+[A-Z]"  # e.g. "1.2.3 Some Title"
)
_UNDERLINE_RE = re.compile(r"^[=\-]{3,}$")


class TextParser(BaseParser):
    """Extracts structured sections from plain text and CSV files.

    Splits on double newlines to identify paragraphs.  Lines that look like
    headings (ALL CAPS, numbered sections, or underlined) are promoted to
    section titles and used to build a hierarchy.
    """

    async def parse(self, file_path: str) -> list[ParsedSection]:
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
        except Exception:
            logger.exception("Failed to read text file: %s", file_path)
            raise

        # Handle CSV-like files: if the first line contains multiple commas
        # and the file is small-ish, treat the whole thing as a table section.
        first_line = raw_text.split("\n", 1)[0] if raw_text else ""
        if first_line.count(",") >= 2:
            return self._parse_as_csv(raw_text)

        return self._parse_as_text(raw_text)

    # ------------------------------------------------------------------
    # Plain text
    # ------------------------------------------------------------------

    def _parse_as_text(self, raw_text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        blocks = re.split(r"\n\s*\n", raw_text)

        hierarchy: list[str] = []
        current_title: str | None = None

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")

            # Check if this block is a heading
            is_heading = False
            heading_text = block

            if len(lines) == 1:
                line = lines[0].strip()
                if _ALL_CAPS_RE.match(line):
                    is_heading = True
                    heading_text = line
                elif _NUMBERED_SECTION_RE.match(line):
                    is_heading = True
                    heading_text = line
            elif len(lines) == 2:
                # Check for underline-style heading:
                #   Some Title
                #   ==========
                if _UNDERLINE_RE.match(lines[1].strip()):
                    is_heading = True
                    heading_text = lines[0].strip()

            if is_heading:
                current_title = heading_text
                hierarchy = [heading_text]
                sections.append(
                    ParsedSection(
                        content=heading_text,
                        page_number=None,
                        section_title=heading_text,
                        section_hierarchy=list(hierarchy),
                        chunk_type="heading",
                    )
                )
            else:
                sections.append(
                    ParsedSection(
                        content=block,
                        page_number=None,
                        section_title=current_title,
                        section_hierarchy=list(hierarchy),
                        chunk_type="paragraph",
                    )
                )

        logger.info("Text parsed: %d sections", len(sections))
        return sections

    # ------------------------------------------------------------------
    # CSV-like text
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_as_csv(raw_text: str) -> list[ParsedSection]:
        """Treat the file as CSV data and return table-type sections."""
        lines = [line for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return []

        sections: list[ParsedSection] = []
        header = lines[0]

        batch_size = 50
        data_lines = lines[1:]

        if not data_lines:
            sections.append(
                ParsedSection(
                    content=header,
                    page_number=None,
                    section_title="CSV Data",
                    section_hierarchy=["CSV Data"],
                    chunk_type="table",
                )
            )
            return sections

        for batch_idx in range(0, len(data_lines), batch_size):
            batch = data_lines[batch_idx : batch_idx + batch_size]
            content = header + "\n" + "\n".join(batch)
            sections.append(
                ParsedSection(
                    content=content,
                    page_number=None,
                    section_title="CSV Data",
                    section_hierarchy=["CSV Data"],
                    chunk_type="table",
                )
            )

        logger.info("CSV parsed: %d sections", len(sections))
        return sections

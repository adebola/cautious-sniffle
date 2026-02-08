"""Abstract base parser for document ingestion."""

from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    """A single parsed section of a document.

    Attributes:
        content: The text content of the section.
        page_number: The page number where this section appears (1-indexed, if applicable).
        section_title: The heading or title of this section, if detected.
        section_hierarchy: Ordered list of ancestor headings, e.g. ["Chapter 1", "1.1 Overview"].
        chunk_type: Semantic type of the section content - "paragraph", "heading", "table", "list".
    """

    content: str
    page_number: int | None = None
    section_title: str | None = None
    section_hierarchy: list[str] | None = field(default_factory=list)
    chunk_type: str = "paragraph"


class BaseParser:
    """Abstract base class for document parsers.

    Each parser is responsible for reading a specific file format and returning
    a list of ``ParsedSection`` objects that represent the logical structure
    of the document.
    """

    async def parse(self, file_path: str) -> list[ParsedSection]:
        """Parse a document file and return structured sections.

        Args:
            file_path: Path to the downloaded file on local disk.

        Returns:
            A list of ParsedSection objects.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError

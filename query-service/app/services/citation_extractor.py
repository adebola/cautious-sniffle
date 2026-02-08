"""Citation extraction from LLM responses."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)


def extract_citations(text: str, sources: list[dict]) -> list[dict]:
    """Parse numbered citation markers from an LLM response and map them to source chunks.

    The LLM is prompted to cite sources using ``[N]`` markers (1-indexed).
    This function finds all such markers in *text* and maps each one to the
    corresponding entry in *sources* (at index N-1).

    Args:
        text: The LLM-generated answer text containing ``[N]`` markers.
        sources: Ordered list of source dicts as returned by the chunk search.
            Each dict is expected to have the shape produced by
            ``QueryProcessor._format_search_results`` -- i.e. keys such as
            ``chunk_id``, ``document_id``, ``document_name``, ``page_number``,
            ``section``, ``content``, and ``similarity``.

    Returns:
        A deduplicated list of citation dicts, each with fields:
        ``id``, ``document_id``, ``document_name``, ``chunk_id``,
        ``page_number``, ``section``, ``excerpt``, ``relevance_score``.
    """
    if not sources:
        return []

    # Find all [N] markers (N is a positive integer)
    pattern = re.compile(r"\[(\d+)]")
    matches = pattern.findall(text)

    if not matches:
        logger.debug("No citation markers found in response text")
        return []

    # Deduplicate while preserving first-seen order
    seen_indices: set[int] = set()
    citations: list[dict] = []

    for match in matches:
        idx = int(match)
        # 1-indexed: map to sources[idx - 1]
        if idx < 1 or idx > len(sources):
            logger.warning("Citation marker [%d] is out of range (have %d sources)", idx, len(sources))
            continue
        if idx in seen_indices:
            continue
        seen_indices.add(idx)

        source = sources[idx - 1]

        # Build an excerpt: first 200 characters of the chunk content
        content = source.get("content", "")
        excerpt = content[:200].strip()
        if len(content) > 200:
            excerpt += "..."

        citation = {
            "id": str(uuid.uuid4()),
            "document_id": source.get("document_id", ""),
            "document_name": source.get("document_name", ""),
            "chunk_id": source.get("chunk_id", ""),
            "page_number": source.get("page_number"),
            "section": source.get("section"),
            "excerpt": excerpt,
            "relevance_score": source.get("similarity", 0.0),
        }
        citations.append(citation)

    logger.info("Extracted %d unique citations from response", len(citations))
    return citations

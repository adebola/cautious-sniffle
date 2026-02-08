"""Document classification using OpenAI chat completion."""

import json
import logging

import tiktoken
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_CLASSIFICATION_SYSTEM_PROMPT = """\
You are a document classification assistant. Analyze the provided document excerpt \
and return a JSON object with the following structure. Do NOT include any text \
outside the JSON object.

{
  "detected_type": "<one of: contract, invoice, report, memo, policy, manual, \
letter, proposal, resume, spreadsheet, legal_filing, academic_paper, presentation, \
meeting_notes, other>",
  "confidence": <float between 0.0 and 1.0>,
  "structure": {
    "has_toc": <boolean - true if a table of contents is detected>,
    "section_count": <integer - estimated number of distinct sections>,
    "has_tables": <boolean - true if tabular data is present>
  },
  "entities": [<list of key named entities found, e.g. company names, person names>],
  "dates_mentioned": [<list of date strings found in the text, in ISO-8601 or original format>]
}
"""

_CLASSIFICATION_USER_PROMPT = """\
Classify the following document excerpt:

---
{text}
---

Return ONLY the JSON object described in your instructions.
"""

# Maximum tokens to sample from the document for classification
_MAX_SAMPLE_TOKENS = 2000


class DocumentClassifier:
    """Classifies documents by sending a text sample to an OpenAI chat model.

    The model is prompted to return structured JSON describing the document type,
    structure, key entities, and mentioned dates.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._enc = tiktoken.get_encoding("cl100k_base")

    async def classify_document(self, text_sample: str) -> dict:
        """Classify a document based on a text sample.

        Args:
            text_sample: A representative excerpt of the document (ideally
                the first ~2000 tokens).

        Returns:
            A dict with keys ``detected_type``, ``confidence``, ``structure``,
            ``entities``, and ``dates_mentioned``.
        """
        # Truncate to token budget
        truncated = self._truncate_to_tokens(text_sample, _MAX_SAMPLE_TOKENS)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _CLASSIFICATION_USER_PROMPT.format(text=truncated),
                    },
                ],
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            result = json.loads(content)

            # Validate expected keys and backfill defaults
            return self._normalise(result)

        except json.JSONDecodeError:
            logger.error("LLM returned non-JSON response for classification")
            return self._default_classification()

        except Exception:
            logger.exception("Document classification failed")
            return self._default_classification()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to at most *max_tokens*."""
        tokens = self._enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._enc.decode(tokens[:max_tokens])

    @staticmethod
    def _normalise(raw: dict) -> dict:
        """Ensure all expected keys are present with reasonable defaults."""
        return {
            "detected_type": raw.get("detected_type", "other"),
            "confidence": float(raw.get("confidence", 0.0)),
            "structure": {
                "has_toc": bool(raw.get("structure", {}).get("has_toc", False)),
                "section_count": int(raw.get("structure", {}).get("section_count", 0)),
                "has_tables": bool(raw.get("structure", {}).get("has_tables", False)),
            },
            "entities": raw.get("entities", []),
            "dates_mentioned": raw.get("dates_mentioned", []),
        }

    @staticmethod
    def _default_classification() -> dict:
        """Return a safe fallback classification result."""
        return {
            "detected_type": "other",
            "confidence": 0.0,
            "structure": {
                "has_toc": False,
                "section_count": 0,
                "has_tables": False,
            },
            "entities": [],
            "dates_mentioned": [],
        }

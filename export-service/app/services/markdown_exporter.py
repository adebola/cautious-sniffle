"""Markdown exporter for query sessions."""

from datetime import datetime, timezone
from io import BytesIO


class MarkdownExporter:
    """Exports a query session as a Markdown (.md) document."""

    def export_session(self, session_data: dict, workspace_name: str) -> BytesIO:
        """Generate a Markdown file from session data.

        Args:
            session_data: Dict containing session metadata and messages.
            workspace_name: The name of the workspace the session belongs to.

        Returns:
            BytesIO buffer containing the generated Markdown (UTF-8 encoded).
        """
        session_title = session_data.get("title", "Untitled Session")
        messages = session_data.get("messages", [])
        export_date = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

        lines: list[str] = []

        # ── Header ─────────────────────────────────────────────────────
        lines.append(f"# {workspace_name} - {session_title}")
        lines.append("")
        lines.append(f"*Exported on {export_date}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Message pairs ─────────────────────────────────────────────
        pairs = self._extract_message_pairs(messages)
        for question, answer, citations in pairs:
            # Question heading
            lines.append(f"## Q: {question}")
            lines.append("")

            # Answer body
            if answer:
                lines.append(answer)
                lines.append("")

            # Citations / sources
            if citations:
                lines.append("**Sources:**")
                for idx, cite in enumerate(citations, start=1):
                    doc_name = cite.get("document_name", "Unknown Document")
                    page = cite.get("page", "N/A")
                    section = cite.get("section", "")

                    cite_line = f"{idx}. {doc_name}, Page {page}"
                    if section:
                        cite_line += f", Section: {section}"
                    lines.append(cite_line)
                lines.append("")

            lines.append("---")
            lines.append("")

        # ── Encode and return ─────────────────────────────────────────
        content = "\n".join(lines)
        buffer = BytesIO(content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    @staticmethod
    def _extract_message_pairs(
        messages: list[dict],
    ) -> list[tuple[str, str, list[dict]]]:
        """Pair up user questions with assistant answers.

        Returns a list of (question, answer, citations) tuples.
        """
        pairs: list[tuple[str, str, list[dict]]] = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg.get("role") == "user":
                question = msg.get("content", "")
                answer = ""
                citations: list[dict] = []

                if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                    assistant_msg = messages[i + 1]
                    answer = assistant_msg.get("content", "")
                    citations = assistant_msg.get("citations", [])
                    i += 2
                else:
                    i += 1

                pairs.append((question, answer, citations))
            else:
                i += 1

        return pairs

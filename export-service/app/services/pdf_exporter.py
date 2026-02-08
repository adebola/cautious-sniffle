"""PDF exporter for query sessions."""

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


class PdfExporter:
    """Exports a query session as a PDF document."""

    def __init__(self):
        self._styles = getSampleStyleSheet()
        self._register_custom_styles()

    def _register_custom_styles(self) -> None:
        """Register custom paragraph styles for the export."""
        self._styles.add(
            ParagraphStyle(
                name="ExportTitle",
                parent=self._styles["Title"],
                fontSize=22,
                leading=26,
                spaceAfter=6,
                textColor=colors.HexColor("#1A1A2E"),
            )
        )
        self._styles.add(
            ParagraphStyle(
                name="ExportDate",
                parent=self._styles["Normal"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#666666"),
                spaceAfter=20,
                fontName="Helvetica-Oblique",
            )
        )
        self._styles.add(
            ParagraphStyle(
                name="Question",
                parent=self._styles["Heading2"],
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#1A56DB"),
                fontName="Helvetica-Bold",
                spaceAfter=8,
            )
        )
        self._styles.add(
            ParagraphStyle(
                name="Answer",
                parent=self._styles["Normal"],
                fontSize=11,
                leading=15,
                spaceAfter=6,
                fontName="Helvetica",
            )
        )
        self._styles.add(
            ParagraphStyle(
                name="Citation",
                parent=self._styles["Normal"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#555555"),
                fontName="Helvetica-Oblique",
                leftIndent=18,
            )
        )

    def export_session(self, session_data: dict, workspace_name: str) -> BytesIO:
        """Generate a PDF file from session data.

        Args:
            session_data: Dict containing session metadata and messages.
            workspace_name: The name of the workspace the session belongs to.

        Returns:
            BytesIO buffer containing the generated PDF file.
        """
        buffer = BytesIO()
        session_title = session_data.get("title", "Untitled Session")
        messages = session_data.get("messages", [])
        export_date = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story: list = []

        # ── Title ──────────────────────────────────────────────────────
        title_text = self._escape_xml(f"{workspace_name} - {session_title}")
        story.append(Paragraph(title_text, self._styles["ExportTitle"]))

        # ── Date ───────────────────────────────────────────────────────
        story.append(Paragraph(f"Exported on {export_date}", self._styles["ExportDate"]))
        story.append(Spacer(1, 12))

        # ── Message pairs ─────────────────────────────────────────────
        pairs = self._extract_message_pairs(messages)
        for question, answer, citations in pairs:
            # Question
            q_text = self._escape_xml(f"Q: {question}")
            story.append(Paragraph(q_text, self._styles["Question"]))
            story.append(Spacer(1, 4))

            # Answer paragraphs
            if answer:
                for paragraph_text in answer.split("\n\n"):
                    stripped = paragraph_text.strip()
                    if stripped:
                        story.append(
                            Paragraph(self._escape_xml(stripped), self._styles["Answer"])
                        )
                        story.append(Spacer(1, 4))

            # Citations
            if citations:
                sources_label = "<b>Sources:</b>"
                story.append(Paragraph(sources_label, self._styles["Answer"]))
                for idx, cite in enumerate(citations, start=1):
                    doc_name = cite.get("document_name", "Unknown Document")
                    page = cite.get("page", "N/A")
                    section = cite.get("section", "")

                    cite_text = f"{idx}. {self._escape_xml(doc_name)}, Page {page}"
                    if section:
                        cite_text += f", Section: {self._escape_xml(section)}"

                    story.append(Paragraph(cite_text, self._styles["Citation"]))

            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape characters that are invalid in ReportLab XML markup."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

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

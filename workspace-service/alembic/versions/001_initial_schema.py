"""Initial workspace service schema.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable uuid-ossp extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── workspace_templates ──────────────────────────────────────────────
    op.create_table(
        "workspace_templates",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column(
            "default_settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "document_types",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("output_instructions", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "display_order",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # ── workspaces ───────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "template_id",
            sa.String(50),
            sa.ForeignKey("workspace_templates.id"),
            nullable=False,
        ),
        sa.Column("system_prompt_override", sa.Text, nullable=True),
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'deleted')",
            name="chk_workspace_status",
        ),
    )
    op.create_index("idx_workspaces_organization", "workspaces", ["organization_id"])
    op.create_index(
        "idx_workspaces_org_status", "workspaces", ["organization_id", "status"]
    )
    op.create_index("idx_workspaces_template", "workspaces", ["template_id"])
    op.create_index("idx_workspaces_created_by", "workspaces", ["created_by"])

    # ── workspace_documents ──────────────────────────────────────────────
    op.create_table(
        "workspace_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "added_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint(
            "workspace_id", "document_id", name="uq_workspace_document"
        ),
    )
    op.create_index(
        "idx_workspace_docs_workspace", "workspace_documents", ["workspace_id"]
    )
    op.create_index(
        "idx_workspace_docs_document", "workspace_documents", ["document_id"]
    )

    # ── workspace_members ────────────────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'member'"),
        ),
        sa.Column(
            "added_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="chk_workspace_role",
        ),
    )
    op.create_index(
        "idx_workspace_members_workspace", "workspace_members", ["workspace_id"]
    )
    op.create_index(
        "idx_workspace_members_user", "workspace_members", ["user_id"]
    )

    # ── query_sessions ───────────────────────────────────────────────────
    op.create_table(
        "query_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "selected_document_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="chk_session_status",
        ),
    )
    op.create_index("idx_sessions_workspace", "query_sessions", ["workspace_id"])
    op.create_index("idx_sessions_user", "query_sessions", ["user_id"])
    op.create_index(
        "idx_sessions_ws_status", "query_sessions", ["workspace_id", "status"]
    )

    # ── messages ─────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("query_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "citations",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "retrieved_chunks",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("token_count_input", sa.Integer, nullable=True),
        sa.Column("token_count_output", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="chk_message_role",
        ),
    )
    op.create_index("idx_messages_session", "messages", ["session_id"])
    op.create_index(
        "idx_messages_session_created", "messages", ["session_id", "created_at"]
    )

    # ── Seed workspace templates ─────────────────────────────────────────
    op.execute("""
INSERT INTO workspace_templates (id, name, description, icon, system_prompt, default_settings, document_types, output_instructions, display_order)
VALUES
('legal_matter', 'Legal Matter', 'For case files, contracts, and legal research', 'scale',
 'You are a legal research assistant. Analyze documents with precision, identify relevant precedents, and provide citations in legal format. Always distinguish between facts and legal interpretation. Never provide legal advice - only analysis and research assistance.

When answering questions:
1. Always cite the specific document, page, and section for each claim
2. Use precise legal terminology
3. Note any ambiguities or conflicting information
4. Distinguish between what the documents state and your analysis',
 '{"citation_style": "legal", "temperature": 0.2, "max_tokens": 2000}'::jsonb,
 ARRAY['contract', 'brief', 'statute', 'case_law', 'evidence', 'correspondence'],
 'Format citations as: [Document Name, Page X, Section Y]. Provide a summary followed by detailed analysis.',
 1),

('medical_case', 'Medical Case', 'For patient records and clinical documentation', 'heart-pulse',
 'You are a clinical documentation assistant. Analyze medical records with attention to clinical details, timeline of care, and guideline compliance. Use proper medical terminology. Never provide medical advice or diagnoses - only documentation analysis.

When answering questions:
1. Reference specific records with dates
2. Note the clinical context
3. Identify any documentation gaps
4. Flag potential compliance issues',
 '{"citation_style": "medical", "temperature": 0.2, "max_tokens": 2000}'::jsonb,
 ARRAY['medical_record', 'lab_result', 'imaging_report', 'clinical_guideline', 'research_paper'],
 'Reference records by type and date. Note any clinical concerns requiring attention.',
 2),

('audit_project', 'Audit Project', 'For financial audits and compliance reviews', 'clipboard-check',
 'You are an audit documentation assistant. Analyze financial documents, identify discrepancies, and track compliance with relevant standards. Maintain objectivity and cite specific evidence for all findings.

When answering questions:
1. Reference specific documents and page numbers
2. Quantify findings where possible
3. Categorize issues by risk level
4. Note relevant standards or regulations',
 '{"citation_style": "reference", "temperature": 0.1, "max_tokens": 2000}'::jsonb,
 ARRAY['financial_statement', 'policy_document', 'regulation', 'correspondence', 'supporting_document'],
 'Provide findings with specific document references. Categorize by risk: High/Medium/Low.',
 3),

('research_project', 'Research Project', 'For academic and professional research', 'book-open',
 'You are a research assistant. Synthesize information from multiple sources, identify themes and patterns, and provide properly formatted citations. Maintain academic rigor and note conflicting findings.

When answering questions:
1. Cite sources in academic format
2. Note methodology and limitations
3. Identify consensus and disagreements
4. Suggest areas for further research',
 '{"citation_style": "academic", "temperature": 0.3, "max_tokens": 2000}'::jsonb,
 ARRAY['research_paper', 'report', 'data_file', 'presentation'],
 'Use academic citation format. Note limitations and conflicting evidence.',
 4),

('consulting', 'Consulting Project', 'For strategy and advisory work', 'briefcase',
 'You are a strategy research assistant. Analyze business documents, identify key insights, and synthesize recommendations. Focus on actionable intelligence and quantifiable findings.

When answering questions:
1. Lead with key insights
2. Support with specific evidence
3. Quantify impact where possible
4. Provide actionable recommendations',
 '{"citation_style": "business", "temperature": 0.3, "max_tokens": 2000}'::jsonb,
 ARRAY['report', 'presentation', 'financial_data', 'market_research', 'correspondence'],
 'Provide executive-style summaries. Quantify findings and cite supporting documents.',
 5),

('general', 'General Workspace', 'Flexible workspace for any document type', 'folder',
 'You are a document analysis assistant. Analyze the provided documents carefully, extract key information, and answer questions based solely on the document contents. Always cite your sources.

When answering questions:
1. Base answers only on provided documents
2. Cite specific pages and sections
3. Note if information is not found
4. Be clear about uncertainty',
 '{"citation_style": "inline", "temperature": 0.3, "max_tokens": 2000}'::jsonb,
 ARRAY[]::text[],
 'Cite sources using [Document, Page X] format.',
 6);
""")


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("query_sessions")
    op.drop_table("workspace_members")
    op.drop_table("workspace_documents")
    op.drop_table("workspaces")
    op.drop_table("workspace_templates")

# ChatCraft Professional - Standalone Product Specification

> **Purpose**: Complete technical specification for building ChatCraft Professional as an independent, standalone product. This document covers all services, database schemas, APIs, and infrastructure required to build the platform from scratch.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema](#4-database-schema)
5. [Service Specifications](#5-service-specifications)
   - 5.1 [API Gateway](#51-api-gateway)
   - 5.2 [Auth Service](#52-auth-service)
   - 5.3 [Organization Service](#53-organization-service)
   - 5.4 [Document Service](#54-document-service)
   - 5.5 [Ingestion Service](#55-ingestion-service)
   - 5.6 [Workspace Service](#56-workspace-service)
   - 5.7 [Query Service](#57-query-service)
   - 5.8 [Billing Service](#58-billing-service)
   - 5.9 [Notification Service](#59-notification-service)
   - 5.10 [Export Service](#510-export-service)
6. [Infrastructure](#6-infrastructure)
7. [Security](#7-security)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Environment Configuration](#9-environment-configuration)
10. [API Standards](#10-api-standards)

---

## 1. Product Overview

### 1.1 What is ChatCraft Professional?

ChatCraft Professional is a document intelligence platform that enables professionals to upload documents, organize them into workspaces (cases, matters, projects), and query them using AI with accurate source citations.

### 1.2 Target Users

| Vertical | Use Case | Key Documents |
|----------|----------|---------------|
| Legal | Case research, contract analysis | Case files, contracts, briefs, statutes |
| Medical | Clinical documentation review | Patient records, guidelines, literature |
| Accounting/Audit | Audit preparation, compliance | Financial statements, policies, regulations |
| Consulting | Research synthesis, due diligence | Reports, market research, presentations |
| Research | Literature review, thesis support | Papers, data files, references |

### 1.3 Core Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORGANIZATION                             │
│  (Company/Firm - the billing entity)                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │    USER     │  │    USER     │  │    USER     │              │
│  │  (Member)   │  │   (Admin)   │  │  (Member)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    DOCUMENT LIBRARY                      │   │
│  │  [Doc1.pdf] [Doc2.docx] [Doc3.pdf] [Doc4.xlsx] ...       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐    │
│  │   WORKSPACE 1   │  │   WORKSPACE 2   │  │  WORKSPACE 3  │    │
│  │ "Smith v Jones" │  │ "Q4 Audit"      │  │ "Research"    │    │
│  │                 │  │                 │  │               │    │
│  │ Docs: 1, 3      │  │ Docs: 2, 4      │  │ Docs: 1, 2, 4 │    │
│  │ Members: A, B   │  │ Members: B, C   │  │ Members: A    │    │
│  │                 │  │                 │  │               │    │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │               │    │
│  │ │  SESSION 1  │ │  │ │  SESSION 1  │ │  │               │    │
│  │ │  Q&A thread │ │  │ │  Q&A thread │ │  │               │    │
│  │ └─────────────┘ │  │ └─────────────┘ │  │               │    │
│  └─────────────────┘  └─────────────────┘  └───────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Organization**: The top-level tenant (a law firm, hospital, accounting firm). Owns all documents and workspaces. Is the billing entity.

**User**: A person within an organization. Has roles (owner, admin, member) at org level.

**Document**: An uploaded file (PDF, DOCX, etc.) stored in the organization's library. Can be added to multiple workspaces.

**Workspace**: A project container (case, matter, audit, research project). Has its own members with roles. Contains references to documents and query sessions.

**Session**: A conversation thread within a workspace where users ask questions and receive cited answers.

**Citation**: A reference to a specific location (page, section) in a source document.

### 1.4 Key Features

1. **Document Upload & Processing**: Upload PDFs, DOCX, XLSX with intelligent parsing
2. **Workspace Organization**: Group documents by project/case/matter
3. **Team Collaboration**: Invite team members with role-based access
4. **AI-Powered Queries**: Ask questions, get answers with citations
5. **Citation Accuracy**: Every claim linked to specific page/section
6. **Session Export**: Export Q&A sessions as professional reports
7. **Audit Trail**: Complete log of all actions for compliance
8. **Industry Templates**: Pre-configured workspaces for legal, medical, audit, etc.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
                                    ┌─────────────────┐
                                    │   Web Client    │
                                    │  (React SPA)    │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY                               │
│                    (Spring Cloud Gateway)                          │
│         • Routing • Rate Limiting • Auth Verification              │
└────────────────────────────────────────────────────────────────────┘
                                             │
           ┌─────────────┬─────────────┬─────┴─────┬─────────────┐
           ▼             ▼             ▼           ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │    Auth     │ │Organization │ │Document │ │Workspace│ │  Query  │
    │   Service   │ │   Service   │ │ Service │ │ Service │ │ Service │
    │   (Java)    │ │  (Python)   │ │(Python) │ │(Python) │ │(Python) │
    └──────┬──────┘ └──────┬──────┘ └────┬────┘ └────┬────┘ └────┬────┘
           │               │              │          │           │
           └───────────────┴──────────────┴──────────┴───────────┘
                                          │
           ┌─────────────┬────────────────┼────────────────┬─────────────┐
           ▼             ▼                ▼                ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐
    │  Ingestion  │ │   Billing   │ │Notification │ │   Export    │ │  Audit  │
    │   Service   │ │   Service   │ │   Service   │ │   Service   │ │ Service │
    │  (Python)   │ │  (Python)   │ │  (Python)   │ │  (Python)   │ │(Python) │
    └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘

┌────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                  │
│  ┌──────────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │   Redis   │  │   MinIO   │  │  RabbitMQ    │  │
│  │  + pgvector  │  │  (Cache)  │  │ (Storage) │  │  (Queue)     │  │
│  └──────────────┘  └───────────┘  └───────────┘  └──────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Inventory

| Service              | Technology | Port | Purpose |
|----------------------|------------|------|---------|
| Gateway Service      | Java Spring Cloud Gateway | 8080 | Routing, rate limiting, auth |
| Auth Service         | Java Spring Boot | 8081 | Authentication, authorization, JWT |
| Organization Service | Python FastAPI | 8082 | Org management, settings, users |
| Document Service     | Python FastAPI | 8083 | Document CRUD, metadata |
| Ingestion Service    | Python FastAPI | 8084 | Parsing, chunking, embedding |
| Workspace Service    | Python FastAPI | 8085 | Workspaces, members, sessions |
| Query Service        | Python FastAPI | 8086 | RAG retrieval, LLM, citations |
| Billing Service      | Python FastAPI | 8087 | Plans, subscriptions, usage |
| Notification Service | Python FastAPI | 8088 | Email, in-app notifications |
| Export Service       | Python FastAPI | 8089 | Report generation (DOCX/PDF) |
| Audit Service        | Python FastAPI | 8090 | Logging, compliance, audit trail |

### 2.3 Request Flow Example

**User asks a question in a workspace:**

```
1. Client → Gateway: POST /api/v1/query
   Headers: Authorization: Bearer <jwt>
   Body: { workspace_id, session_id, question, selected_doc_ids }

2. Gateway → Auth Service: Validate JWT
   Returns: { user_id, org_id, roles }

3. Gateway → Query Service: Forward request with user context

4. Query Service → Workspace Service: Verify workspace access
   GET /internal/workspaces/{id}/access?user_id=xxx
   Returns: { has_access: true, role: "member" }

5. Query Service → Document Service: Get document chunk IDs
   POST /internal/documents/chunks/search
   Body: { document_ids, query_embedding, top_k: 10 }
   Returns: [{ chunk_id, content, citation_metadata, score }]

6. Query Service → LLM: Generate response with sources
   Returns: Answer with [1], [2] citation markers

7. Query Service → Audit Service: Log query
   POST /internal/audit/log
   Body: { action: "query_executed", ... }

8. Query Service → Client: Return response with citations
```

---

## 3. Technology Stack

### 3.1 Backend Services

| Component | Technology                              | Rationale |
|-----------|-----------------------------------------|-----------|
| API Gateway | Spring Cloud Gateway (Java 21)          | Robust, proven, excellent Spring Security integration |
| Auth Service | Spring Boot + Spring Security (Java 21) | OAuth 2.0 / OpenID Connect, JWT handling |
| Other Services | Python 3.12 + FastAPI                   | Rapid development, excellent AI/ML ecosystem |
| ORM | SQLAlchemy 2.0 (Python), JPA (Java)     | Type-safe, async support |
| Validation | Pydantic v2 (Python)                    | Runtime validation, serialization |

### 3.2 Data Stores

| Component | Technology | Purpose |
|-----------|------------|---------|
| Primary Database | PostgreSQL 16 | Relational data, ACID compliance |
| Vector Store | pgvector extension | Embedding storage and similarity search |
| Cache | Redis 7 | Session cache, rate limiting, hot data |
| Object Storage | MinIO | Document file storage (S3-compatible) |
| Message Queue | RabbitMQ | Async job processing |

### 3.3 AI/ML

| Component | Options | Notes |
|-----------|---------|-------|
| LLM Provider | OpenAI GPT-4, Anthropic Claude | Primary: GPT-4o for cost/quality balance |
| Embeddings | OpenAI text-embedding-3-small | 1536 dimensions, good quality/cost |
| Document Parsing | PyMuPDF, python-docx, unstructured | Multi-format support |
| OCR (if needed) | Tesseract, Azure Document Intelligence | For scanned documents |

### 3.4 Frontend

#### Web Application
| Component | Technology |
|-----------|------------|
| Framework | Angular 17+ |
| State Management | NgRx or Angular Signals |
| UI Components | Angular Material or PrimeNG |
| HTTP Client | Built-in HttpClient |
| Build Tool | Angular CLI |

#### Mobile Application
| Component | Technology |
|-----------|------------|
| Framework | Flutter 3.x |
| State Management | Riverpod or BLoC |
| UI Components | Material 3 (built-in) |
| HTTP Client | Dio |
| Local Storage | flutter_secure_storage, Hive |
| File Handling | file_picker, path_provider |

#### Shared Assets
| Asset | Approach |
|-------|----------|
| API Contracts | OpenAPI spec → generate clients for both |
| Design Tokens | Shared JSON (colors, spacing, typography) |
| Icons | Same icon set (Material Icons works in both) |

### 3.5 Infrastructure

| Component | Technology |
|-----------|------------|
| Container Orchestration | Google Kubernetes Engine (GKE) |
| Container Runtime | Docker |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |
| Logging | ELK Stack or Loki |
| Secrets | Google Secret Manager |

---

## 4. Database Schema

### 4.1 Complete Schema

```sql
-- =====================================================
-- EXTENSIONS
-- =====================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- =====================================================
-- ORGANIZATIONS & USERS
-- =====================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    logo_url VARCHAR(500),
    settings JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_org_status CHECK (status IN ('active', 'suspended', 'cancelled'))
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_status ON organizations(status);

-- Organization settings JSONB structure:
-- {
--   "timezone": "Africa/Lagos",
--   "default_workspace_template": "general",
--   "allowed_templates": ["legal_matter", "audit_project", ...],
--   "features": {
--     "export_enabled": true,
--     "api_access": false,
--     "custom_templates": false
--   }
-- }

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    avatar_url VARCHAR(500),
    settings JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    email_verified_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_user_email_org UNIQUE (organization_id, email),
    CONSTRAINT chk_user_role CHECK (role IN ('owner', 'admin', 'member')),
    CONSTRAINT chk_user_status CHECK (status IN ('active', 'invited', 'suspended', 'deleted'))
);

CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(organization_id, status);

-- User settings JSONB structure:
-- {
--   "notifications": {
--     "email_workspace_invite": true,
--     "email_weekly_digest": false
--   },
--   "preferences": {
--     "default_export_format": "docx",
--     "citation_style": "inline"
--   }
-- }

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    device_info JSONB,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_password_reset_user ON password_reset_tokens(user_id);

-- =====================================================
-- DOCUMENTS
-- =====================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    
    -- File information
    original_filename VARCHAR(500) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(64),
    
    -- Metadata
    title VARCHAR(500),
    description TEXT,
    document_type VARCHAR(50),
    language VARCHAR(10) DEFAULT 'en',
    page_count INT,
    
    -- Classification (populated by Ingestion Service)
    classification JSONB NOT NULL DEFAULT '{}',
    
    -- Processing status
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processing_error TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_doc_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_documents_organization ON documents(organization_id);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_status ON documents(organization_id, processing_status);
CREATE INDEX idx_documents_type ON documents(organization_id, document_type);
CREATE INDEX idx_documents_deleted ON documents(organization_id, deleted_at);

-- Classification JSONB structure:
-- {
--   "detected_type": "contract",
--   "confidence": 0.92,
--   "structure": {
--     "has_toc": true,
--     "section_count": 8,
--     "has_tables": true,
--     "has_images": false
--   },
--   "entities": ["Acme Corp", "John Smith"],
--   "dates_mentioned": ["2024-01-15", "2024-12-31"]
-- }

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_type VARCHAR(50) NOT NULL DEFAULT 'paragraph',
    
    -- Citation metadata
    page_number INT,
    section_title VARCHAR(500),
    section_hierarchy TEXT[],
    clause_number VARCHAR(50),
    
    -- Embedding
    embedding vector(1536),
    
    -- Metadata
    token_count INT,
    metadata JSONB NOT NULL DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_chunk_type CHECK (chunk_type IN (
        'heading', 'paragraph', 'clause', 'list_item', 
        'table', 'table_row', 'figure_caption', 'footnote', 'quote'
    ))
);

CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_page ON document_chunks(document_id, page_number);
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =====================================================
-- WORKSPACES
-- =====================================================

CREATE TABLE workspace_templates (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    system_prompt TEXT NOT NULL,
    default_settings JSONB NOT NULL DEFAULT '{}',
    document_types TEXT[] NOT NULL DEFAULT '{}',
    output_instructions TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INT NOT NULL DEFAULT 0
);

-- Seed workspace templates
INSERT INTO workspace_templates (id, name, description, icon, system_prompt, default_settings, document_types, output_instructions, display_order) VALUES
('legal_matter', 'Legal Matter', 'For case files, contracts, and legal research', 'scale', 
 'You are a legal research assistant. Analyze documents with precision, identify relevant precedents, and provide citations in legal format. Always distinguish between facts and legal interpretation. Never provide legal advice - only analysis and research assistance.

When answering questions:
1. Always cite the specific document, page, and section for each claim
2. Use precise legal terminology
3. Note any ambiguities or conflicting information
4. Distinguish between what the documents state and your analysis',
 '{"citation_style": "legal", "temperature": 0.2, "max_tokens": 2000}',
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
 '{"citation_style": "medical", "temperature": 0.2, "max_tokens": 2000}',
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
 '{"citation_style": "reference", "temperature": 0.1, "max_tokens": 2000}',
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
 '{"citation_style": "academic", "temperature": 0.3, "max_tokens": 2000}',
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
 '{"citation_style": "business", "temperature": 0.3, "max_tokens": 2000}',
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
 '{"citation_style": "inline", "temperature": 0.3, "max_tokens": 2000}',
 ARRAY[],
 'Cite sources using [Document, Page X] format.',
 6);

CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_id VARCHAR(50) NOT NULL REFERENCES workspace_templates(id),
    
    -- Custom settings (overrides template)
    system_prompt_override TEXT,
    settings JSONB NOT NULL DEFAULT '{}',
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    
    -- Ownership
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_workspace_status CHECK (status IN ('active', 'archived', 'deleted'))
);

CREATE INDEX idx_workspaces_organization ON workspaces(organization_id);
CREATE INDEX idx_workspaces_status ON workspaces(organization_id, status);
CREATE INDEX idx_workspaces_template ON workspaces(template_id);
CREATE INDEX idx_workspaces_created_by ON workspaces(created_by);

-- Workspace settings JSONB structure:
-- {
--   "default_model": "gpt-4o",
--   "temperature": 0.3,
--   "max_tokens": 2000,
--   "citation_style": "inline",
--   "export_format": "docx",
--   "require_document_selection": false,
--   "allow_web_search": false
-- }

CREATE TABLE workspace_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    added_by UUID NOT NULL REFERENCES users(id),
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    notes TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    
    CONSTRAINT uq_workspace_document UNIQUE (workspace_id, document_id)
);

CREATE INDEX idx_workspace_docs_workspace ON workspace_documents(workspace_id);
CREATE INDEX idx_workspace_docs_document ON workspace_documents(document_id);

CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    added_by UUID NOT NULL REFERENCES users(id),
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id),
    CONSTRAINT chk_workspace_role CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
);

CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id);
CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);

-- =====================================================
-- QUERY SESSIONS & MESSAGES
-- =====================================================

CREATE TABLE query_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    title VARCHAR(255),
    description TEXT,
    selected_document_ids UUID[] NOT NULL DEFAULT '{}',
    
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_session_status CHECK (status IN ('active', 'completed', 'archived'))
);

CREATE INDEX idx_sessions_workspace ON query_sessions(workspace_id);
CREATE INDEX idx_sessions_user ON query_sessions(user_id);
CREATE INDEX idx_sessions_status ON query_sessions(workspace_id, status);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES query_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    
    -- Citations (for assistant messages)
    citations JSONB NOT NULL DEFAULT '[]',
    
    -- RAG context (for debugging/audit)
    retrieved_chunks JSONB NOT NULL DEFAULT '[]',
    
    -- Metadata
    model_used VARCHAR(50),
    token_count_input INT,
    token_count_output INT,
    latency_ms INT,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_message_role CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_created ON messages(session_id, created_at);

-- Citations JSONB structure:
-- [
--   {
--     "id": "1",
--     "document_id": "uuid",
--     "document_name": "Contract.pdf",
--     "chunk_id": "uuid",
--     "page_number": 5,
--     "section": "3.2 Payment Terms",
--     "excerpt": "Payment shall be due within 30 days...",
--     "relevance_score": 0.94
--   }
-- ]

-- =====================================================
-- BILLING
-- =====================================================

CREATE TABLE plans (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Pricing (in smallest currency unit, e.g., kobo for NGN)
    price_monthly BIGINT,
    price_annual BIGINT,
    currency VARCHAR(3) NOT NULL DEFAULT 'NGN',
    
    -- Limits
    limits JSONB NOT NULL,
    
    -- Features
    features JSONB NOT NULL DEFAULT '{}',
    
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INT NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed plans
INSERT INTO plans (id, name, description, price_monthly, price_annual, currency, limits, features, display_order) VALUES
('starter', 'Professional Starter', 'For individuals and small teams', 15000000, 150000000, 'NGN',
 '{"max_workspaces": 5, "max_documents": 50, "max_team_members": 2, "monthly_queries": 500, "storage_gb": 5}',
 '{"export": true, "api_access": false, "custom_templates": false, "audit_retention_days": 90, "priority_support": false}',
 1),
 
('growth', 'Professional Growth', 'For growing teams', 40000000, 400000000, 'NGN',
 '{"max_workspaces": 20, "max_documents": 200, "max_team_members": 10, "monthly_queries": 2000, "storage_gb": 20}',
 '{"export": true, "api_access": true, "custom_templates": false, "audit_retention_days": 365, "priority_support": true}',
 2),
 
('enterprise', 'Professional Enterprise', 'For large organizations', NULL, NULL, 'NGN',
 '{"max_workspaces": -1, "max_documents": -1, "max_team_members": -1, "monthly_queries": -1, "storage_gb": -1}',
 '{"export": true, "api_access": true, "custom_templates": true, "audit_retention_days": -1, "priority_support": true, "sso": true, "on_premise": true}',
 3);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES plans(id),
    
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    billing_cycle VARCHAR(20) NOT NULL,
    
    -- Current period
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Trial
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    
    -- Cancellation
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Payment provider
    payment_provider VARCHAR(50),
    payment_provider_subscription_id VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_sub_status CHECK (status IN ('active', 'trialing', 'past_due', 'cancelled', 'unpaid')),
    CONSTRAINT chk_billing_cycle CHECK (billing_cycle IN ('monthly', 'annual'))
);

CREATE INDEX idx_subscriptions_organization ON subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);

CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Usage counts
    workspace_count INT NOT NULL DEFAULT 0,
    document_count INT NOT NULL DEFAULT 0,
    query_count INT NOT NULL DEFAULT 0,
    storage_bytes BIGINT NOT NULL DEFAULT 0,
    team_member_count INT NOT NULL DEFAULT 0,
    
    -- Token usage
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_usage_period UNIQUE (organization_id, period_start)
);

CREATE INDEX idx_usage_organization ON usage_records(organization_id);
CREATE INDEX idx_usage_period ON usage_records(period_start, period_end);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    
    -- Amounts (in smallest currency unit)
    subtotal BIGINT NOT NULL,
    tax BIGINT NOT NULL DEFAULT 0,
    total BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'NGN',
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    
    -- Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Payment
    paid_at TIMESTAMP WITH TIME ZONE,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    
    -- Line items
    line_items JSONB NOT NULL DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    due_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT chk_invoice_status CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible'))
);

CREATE INDEX idx_invoices_organization ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due ON invoices(due_at);

-- =====================================================
-- AUDIT LOGS
-- =====================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Action details
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    
    -- Context
    details JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_organization ON audit_logs(organization_id);
CREATE INDEX idx_audit_workspace ON audit_logs(workspace_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Partition audit logs by month for performance
-- CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- =====================================================
-- NOTIFICATIONS
-- =====================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    
    -- Link to related resource
    resource_type VARCHAR(50),
    resource_id UUID,
    
    -- Status
    read_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, read_at) WHERE read_at IS NULL;

-- =====================================================
-- API KEYS (for API access feature)
-- =====================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    
    name VARCHAR(100) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    
    scopes TEXT[] NOT NULL DEFAULT '{}',
    
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_organization ON api_keys(organization_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON query_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_updated_at BEFORE UPDATE ON usage_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (Multi-tenancy)
-- =====================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (to be applied based on application's auth context)
-- CREATE POLICY org_isolation ON documents
--     USING (organization_id = current_setting('app.current_organization_id')::uuid);
```

### 4.2 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│  organizations  │───────│      users      │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │    ┌────────────────────┼────────────────────┐
         │    │                    │                    │
         ▼    ▼                    ▼                    ▼
┌─────────────────┐       ┌─────────────────┐  ┌─────────────────┐
│    documents    │       │   workspaces    │  │  subscriptions  │
└────────┬────────┘       └────────┬────────┘  └─────────────────┘
         │                         │
         │                         ├─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ document_chunks │       │workspace_members│       │ query_sessions  │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
         ▲                         ▲                         │
         │                         │                         ▼
         │                ┌────────┴────────┐       ┌─────────────────┐
         │                │workspace_documents      │    messages     │
         └────────────────┴─────────────────┘       └─────────────────┘
```

---

## 5. Service Specifications

### 5.1 API Gateway

**Technology**: Spring Cloud Gateway (Java 21)  
**Port**: 8080

#### Purpose
- Route requests to appropriate backend services
- Rate limiting
- JWT validation
- Request/response logging
- CORS handling

#### Configuration

```yaml
# application.yml
server:
  port: 8080

spring:
  cloud:
    gateway:
      default-filters:
        - name: RequestRateLimiter
          args:
            redis-rate-limiter.replenishRate: 100
            redis-rate-limiter.burstCapacity: 200
            key-resolver: "#{@userKeyResolver}"
        - AddRequestHeader=X-Request-ID, ${random.uuid}
        - DedupeResponseHeader=Access-Control-Allow-Origin
      
      routes:
        # Auth Service
        - id: auth-service
          uri: lb://auth-service
          predicates:
            - Path=/api/v1/auth/**
          filters:
            - StripPrefix=0
        
        # Organization Service
        - id: organization-service
          uri: lb://organization-service
          predicates:
            - Path=/api/v1/organizations/**, /api/v1/users/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter
        
        # Document Service
        - id: document-service
          uri: lb://document-service
          predicates:
            - Path=/api/v1/documents/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter
        
        # Workspace Service
        - id: workspace-service
          uri: lb://workspace-service
          predicates:
            - Path=/api/v1/workspaces/**, /api/v1/templates/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter
        
        # Query Service
        - id: query-service
          uri: lb://query-service
          predicates:
            - Path=/api/v1/query/**, /api/v1/sessions/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter
        
        # Billing Service
        - id: billing-service
          uri: lb://billing-service
          predicates:
            - Path=/api/v1/billing/**, /api/v1/subscriptions/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter
        
        # Export Service
        - id: export-service
          uri: lb://export-service
          predicates:
            - Path=/api/v1/exports/**
          filters:
            - StripPrefix=0
            - name: JwtAuthFilter

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus
```

#### JWT Filter

```java
@Component
public class JwtAuthFilter implements GatewayFilter {
    
    private final JwtValidator jwtValidator;
    
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
        
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return unauthorized(exchange);
        }
        
        String token = authHeader.substring(7);
        
        try {
            JwtClaims claims = jwtValidator.validate(token);
            
            // Add user context to headers for downstream services
            ServerHttpRequest request = exchange.getRequest().mutate()
                .header("X-User-ID", claims.getUserId())
                .header("X-Organization-ID", claims.getOrganizationId())
                .header("X-User-Role", claims.getRole())
                .build();
            
            return chain.filter(exchange.mutate().request(request).build());
        } catch (JwtException e) {
            return unauthorized(exchange);
        }
    }
    
    private Mono<Void> unauthorized(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        return exchange.getResponse().setComplete();
    }
}
```

---

### 5.2 Auth Service

**Technology**: Spring Boot + Spring Security (Java 21)  
**Port**: 8081

#### Purpose
- User authentication (login, logout)
- JWT token generation and refresh
- Password management (reset, change)
- OAuth 2.0 provider (optional: Google, Microsoft SSO)

#### Dependencies

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.12.3</version>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
</dependencies>
```

#### API Endpoints

```yaml
# Auth Service API

POST /api/v1/auth/register:
  description: Register new organization and admin user
  request:
    organization_name: string
    email: string
    password: string
    first_name: string
    last_name: string
  response:
    user: User
    organization: Organization
    access_token: string
    refresh_token: string

POST /api/v1/auth/login:
  description: Authenticate user
  request:
    email: string
    password: string
  response:
    user: User
    access_token: string
    refresh_token: string
    expires_in: number

POST /api/v1/auth/refresh:
  description: Refresh access token
  request:
    refresh_token: string
  response:
    access_token: string
    refresh_token: string
    expires_in: number

POST /api/v1/auth/logout:
  description: Revoke refresh token
  headers:
    Authorization: Bearer <access_token>
  request:
    refresh_token: string

POST /api/v1/auth/forgot-password:
  description: Send password reset email
  request:
    email: string

POST /api/v1/auth/reset-password:
  description: Reset password with token
  request:
    token: string
    password: string

POST /api/v1/auth/change-password:
  description: Change password (authenticated)
  headers:
    Authorization: Bearer <access_token>
  request:
    current_password: string
    new_password: string

GET /api/v1/auth/me:
  description: Get current user info
  headers:
    Authorization: Bearer <access_token>
  response:
    user: User
    organization: Organization

# Internal endpoints (service-to-service)
GET /internal/auth/validate:
  description: Validate JWT token
  headers:
    Authorization: Bearer <token>
  response:
    valid: boolean
    claims: JwtClaims
```

#### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "org_id": "organization-uuid",
  "org_slug": "acme-corp",
  "role": "admin",
  "email": "user@example.com",
  "name": "John Doe",
  "iat": 1704067200,
  "exp": 1704070800,
  "iss": "chatcraft-professional",
  "aud": "chatcraft-professional-api"
}
```

#### Implementation Notes

```java
@Service
public class AuthService {
    
    private final UserRepository userRepository;
    private final OrganizationRepository organizationRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    
    @Transactional
    public AuthResponse register(RegisterRequest request) {
        // 1. Validate email not already used
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new EmailAlreadyExistsException();
        }
        
        // 2. Create organization
        Organization org = Organization.builder()
            .name(request.getOrganizationName())
            .slug(generateSlug(request.getOrganizationName()))
            .email(request.getEmail())
            .build();
        org = organizationRepository.save(org);
        
        // 3. Create user as owner
        User user = User.builder()
            .organizationId(org.getId())
            .email(request.getEmail())
            .passwordHash(passwordEncoder.encode(request.getPassword()))
            .firstName(request.getFirstName())
            .lastName(request.getLastName())
            .role(UserRole.OWNER)
            .build();
        user = userRepository.save(user);
        
        // 4. Generate tokens
        String accessToken = jwtService.generateAccessToken(user, org);
        String refreshToken = jwtService.generateRefreshToken(user);
        
        // 5. Store refresh token
        saveRefreshToken(user.getId(), refreshToken);
        
        return AuthResponse.builder()
            .user(UserDto.from(user))
            .organization(OrganizationDto.from(org))
            .accessToken(accessToken)
            .refreshToken(refreshToken)
            .expiresIn(jwtService.getAccessTokenExpiry())
            .build();
    }
    
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
            .orElseThrow(InvalidCredentialsException::new);
        
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new InvalidCredentialsException();
        }
        
        if (user.getStatus() != UserStatus.ACTIVE) {
            throw new UserNotActiveException();
        }
        
        Organization org = organizationRepository.findById(user.getOrganizationId())
            .orElseThrow();
        
        String accessToken = jwtService.generateAccessToken(user, org);
        String refreshToken = jwtService.generateRefreshToken(user);
        
        saveRefreshToken(user.getId(), refreshToken);
        updateLastLogin(user);
        
        return AuthResponse.builder()
            .user(UserDto.from(user))
            .accessToken(accessToken)
            .refreshToken(refreshToken)
            .expiresIn(jwtService.getAccessTokenExpiry())
            .build();
    }
}
```

---

### 5.3 Organization Service

**Technology**: Python FastAPI  
**Port**: 8082

#### Purpose
- Organization CRUD
- User management within organization
- Organization settings
- Team invitations

#### API Endpoints

```python
# Organization Service API

# ============ Organizations ============

@router.get("/organizations/current")
async def get_current_organization(
    current_user: User = Depends(get_current_user)
) -> OrganizationResponse:
    """Get the current user's organization"""
    pass

@router.put("/organizations/current")
async def update_organization(
    data: OrganizationUpdate,
    current_user: User = Depends(get_current_user)
) -> OrganizationResponse:
    """Update organization (admin only)"""
    pass

@router.get("/organizations/current/usage")
async def get_organization_usage(
    current_user: User = Depends(get_current_user)
) -> UsageResponse:
    """Get current usage vs limits"""
    pass

# ============ Users ============

@router.get("/users")
async def list_users(
    status: Optional[UserStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> UserListResponse:
    """List users in organization"""
    pass

@router.post("/users/invite")
async def invite_user(
    data: UserInvite,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Invite a new user to the organization (admin only)"""
    # Creates user with status='invited', sends email
    pass

@router.post("/users/accept-invite")
async def accept_invite(
    data: AcceptInvite
) -> AuthResponse:
    """Accept invitation and set password"""
    pass

@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get user details"""
    pass

@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Update user (admin or self)"""
    pass

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    data: RoleUpdate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Change user's organization role (owner only)"""
    pass

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Deactivate user (admin only)"""
    pass

@router.get("/users/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current user's profile"""
    pass

@router.put("/users/me")
async def update_current_user_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Update current user's profile"""
    pass

@router.put("/users/me/settings")
async def update_user_settings(
    data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Update current user's settings"""
    pass

# ============ Internal Endpoints ============

@router.get("/internal/organizations/{org_id}")
async def internal_get_organization(org_id: UUID) -> OrganizationInternal:
    """Internal: Get organization details"""
    pass

@router.get("/internal/organizations/{org_id}/limits")
async def internal_get_limits(org_id: UUID) -> OrganizationLimits:
    """Internal: Get organization limits from plan"""
    pass

@router.get("/internal/users/{user_id}")
async def internal_get_user(user_id: UUID) -> UserInternal:
    """Internal: Get user details"""
    pass

@router.post("/internal/users/batch")
async def internal_get_users_batch(user_ids: List[UUID]) -> List[UserInternal]:
    """Internal: Get multiple users"""
    pass
```

#### Models

```python
# Pydantic models for Organization Service

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    logo_url: Optional[str]
    settings: dict
    status: str
    created_at: datetime
    
class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    settings: Optional[dict] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    avatar_url: Optional[str]
    status: str
    last_login_at: Optional[datetime]
    created_at: datetime

class UserInvite(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "member"

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UsageResponse(BaseModel):
    workspace_count: int
    workspace_limit: int
    document_count: int
    document_limit: int
    team_member_count: int
    team_member_limit: int
    queries_this_month: int
    query_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
```

---

### 5.4 Document Service

**Technology**: Python FastAPI  
**Port**: 8083

#### Purpose
- Document upload handling
- Document metadata management
- Document retrieval
- Presigned URLs for download

#### API Endpoints

```python
# Document Service API

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """
    Upload a new document.
    
    1. Validate file type and size
    2. Check organization document limit
    3. Upload to MinIO
    4. Create document record
    5. Queue for processing
    """
    pass

@router.post("/documents/upload/batch")
async def upload_documents_batch(
    files: List[UploadFile],
    current_user: User = Depends(get_current_user)
) -> List[DocumentResponse]:
    """Upload multiple documents"""
    pass

@router.get("/documents")
async def list_documents(
    status: Optional[ProcessingStatus] = None,
    document_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user)
) -> DocumentListResponse:
    """List documents in organization"""
    pass

@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> DocumentDetailResponse:
    """Get document details including classification"""
    pass

@router.put("/documents/{document_id}")
async def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Update document metadata"""
    pass

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Soft delete document"""
    pass

@router.get("/documents/{document_id}/download")
async def get_download_url(
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> DownloadUrlResponse:
    """Get presigned URL for download"""
    pass

@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Reprocess document (re-run ingestion)"""
    pass

@router.get("/documents/{document_id}/preview")
async def get_document_preview(
    document_id: UUID,
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user)
) -> PreviewResponse:
    """Get document page preview (image)"""
    pass

# ============ Internal Endpoints ============

@router.get("/internal/documents/{document_id}")
async def internal_get_document(document_id: UUID) -> DocumentInternal:
    """Internal: Get document details"""
    pass

@router.post("/internal/documents/batch")
async def internal_get_documents_batch(
    document_ids: List[UUID]
) -> List[DocumentInternal]:
    """Internal: Get multiple documents"""
    pass

@router.put("/internal/documents/{document_id}/status")
async def internal_update_processing_status(
    document_id: UUID,
    status: ProcessingStatus,
    error: Optional[str] = None
) -> None:
    """Internal: Update processing status (from Ingestion Service)"""
    pass

@router.post("/internal/documents/chunks/search")
async def internal_search_chunks(
    request: ChunkSearchRequest
) -> List[ChunkSearchResult]:
    """
    Internal: Search document chunks by embedding.
    Used by Query Service for RAG retrieval.
    """
    pass
```

#### Models

```python
class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    title: Optional[str]
    description: Optional[str]
    file_size: int
    mime_type: str
    document_type: Optional[str]
    page_count: Optional[int]
    processing_status: str
    uploaded_by: UUID
    uploaded_by_name: str
    created_at: datetime

class DocumentDetailResponse(DocumentResponse):
    classification: dict
    storage_path: str
    file_hash: Optional[str]
    processed_at: Optional[datetime]
    workspace_count: int  # Number of workspaces using this document

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None

class ChunkSearchRequest(BaseModel):
    document_ids: List[UUID]
    query_embedding: List[float]
    top_k: int = 10
    similarity_threshold: float = 0.7

class ChunkSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    content: str
    page_number: Optional[int]
    section_title: Optional[str]
    section_hierarchy: List[str]
    clause_number: Optional[str]
    chunk_type: str
    similarity_score: float
```

#### File Storage

```python
class MinIOStorageService:
    """Handle file storage with MinIO"""
    
    def __init__(self, settings: Settings):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket = settings.minio_bucket
    
    async def upload(
        self, 
        file: UploadFile, 
        organization_id: UUID
    ) -> str:
        """Upload file and return storage path"""
        
        # Generate unique path
        file_ext = Path(file.filename).suffix
        storage_path = f"{organization_id}/{uuid4()}{file_ext}"
        
        # Upload
        self.client.put_object(
            self.bucket,
            storage_path,
            file.file,
            length=-1,
            part_size=10*1024*1024,
            content_type=file.content_type
        )
        
        return storage_path
    
    async def get_presigned_url(
        self, 
        storage_path: str, 
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate presigned download URL"""
        return self.client.presigned_get_object(
            self.bucket,
            storage_path,
            expires=expires
        )
    
    async def delete(self, storage_path: str) -> None:
        """Delete file"""
        self.client.remove_object(self.bucket, storage_path)
```

---

### 5.5 Ingestion Service

**Technology**: Python FastAPI  
**Port**: 8084

#### Purpose
- Document parsing (PDF, DOCX, XLSX, etc.)
- Text extraction with structure preservation
- Chunking with citation metadata
- Embedding generation
- Document classification

#### Architecture

```
                     ┌─────────────────┐
                     │   RabbitMQ      │
                     │ (document.new)  │
                     └────────┬────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION SERVICE                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Parser     │ -> │   Chunker    │ -> │  Embedder    │       │
│  │  (by type)   │    │  (smart)     │    │  (OpenAI)    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Classifier   │    │  Metadata    │    │   Store      │       │
│  │ (doc type)   │    │  Extractor   │    │  (chunks)    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

#### API Endpoints

```python
# Ingestion Service API (mostly internal/worker)

# Manual trigger (for reprocessing)
@router.post("/internal/ingest/{document_id}")
async def ingest_document(document_id: UUID) -> IngestionResult:
    """Manually trigger document ingestion"""
    pass

# Status check
@router.get("/internal/ingest/{document_id}/status")
async def get_ingestion_status(document_id: UUID) -> IngestionStatus:
    """Get ingestion status for a document"""
    pass

# Health check
@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    pass
```

#### Document Parser

```python
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class ParsedPage:
    page_number: int
    content: str
    sections: List['ParsedSection']
    tables: List['ParsedTable']
    images: List['ParsedImage']

@dataclass
class ParsedSection:
    title: str
    level: int
    content: str
    start_page: int
    end_page: int

@dataclass 
class ParsedDocument:
    pages: List[ParsedPage]
    sections: List[ParsedSection]
    metadata: dict
    toc: List[dict]  # Table of contents

class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        pass

class PDFParser(DocumentParser):
    """Parse PDF documents using PyMuPDF"""
    
    async def parse(self, file_path: str) -> ParsedDocument:
        import fitz  # PyMuPDF
        
        doc = fitz.open(file_path)
        pages = []
        
        for page_num, page in enumerate(doc, 1):
            # Extract text with position info
            blocks = page.get_text("dict")["blocks"]
            
            content = ""
            sections = []
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            font_size = span["size"]
                            is_bold = "bold" in span["font"].lower()
                            
                            # Detect headings by font size
                            if font_size > 14 or is_bold:
                                sections.append(ParsedSection(
                                    title=text.strip(),
                                    level=1 if font_size > 16 else 2,
                                    content="",
                                    start_page=page_num,
                                    end_page=page_num
                                ))
                            
                            content += text + " "
            
            pages.append(ParsedPage(
                page_number=page_num,
                content=content.strip(),
                sections=sections,
                tables=[],
                images=[]
            ))
        
        doc.close()
        
        return ParsedDocument(
            pages=pages,
            sections=self._merge_sections(pages),
            metadata=self._extract_metadata(file_path),
            toc=self._extract_toc(file_path)
        )

class DocxParser(DocumentParser):
    """Parse DOCX documents using python-docx"""
    
    async def parse(self, file_path: str) -> ParsedDocument:
        from docx import Document
        
        doc = Document(file_path)
        # ... implementation
        pass

class ParserFactory:
    """Factory to get appropriate parser for file type"""
    
    parsers = {
        'application/pdf': PDFParser,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocxParser,
        # Add more parsers
    }
    
    @classmethod
    def get_parser(cls, mime_type: str) -> DocumentParser:
        parser_class = cls.parsers.get(mime_type)
        if not parser_class:
            raise UnsupportedFileTypeError(mime_type)
        return parser_class()
```

#### Smart Chunker

```python
@dataclass
class Chunk:
    content: str
    chunk_index: int
    chunk_type: str
    page_number: int
    section_title: Optional[str]
    section_hierarchy: List[str]
    clause_number: Optional[str]
    token_count: int

class SmartChunker:
    """
    Intelligent chunking that preserves document structure
    and maintains citation metadata.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 500,  # tokens
        overlap: int = 50,  # tokens
        tokenizer: str = "cl100k_base"
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding(tokenizer)
    
    async def chunk(self, parsed_doc: ParsedDocument) -> List[Chunk]:
        chunks = []
        chunk_index = 0
        current_section = []
        
        for page in parsed_doc.pages:
            # Track current section hierarchy
            for section in page.sections:
                current_section = self._update_hierarchy(current_section, section)
            
            # Split content into paragraphs
            paragraphs = self._split_paragraphs(page.content)
            
            for para in paragraphs:
                para_tokens = len(self.encoding.encode(para))
                
                if para_tokens <= self.max_chunk_size:
                    # Paragraph fits in one chunk
                    chunks.append(Chunk(
                        content=para,
                        chunk_index=chunk_index,
                        chunk_type=self._detect_type(para),
                        page_number=page.page_number,
                        section_title=current_section[-1] if current_section else None,
                        section_hierarchy=current_section.copy(),
                        clause_number=self._extract_clause_number(para),
                        token_count=para_tokens
                    ))
                    chunk_index += 1
                else:
                    # Split large paragraph with overlap
                    sub_chunks = self._split_with_overlap(para, page.page_number, current_section)
                    for sub in sub_chunks:
                        sub.chunk_index = chunk_index
                        chunks.append(sub)
                        chunk_index += 1
        
        return chunks
    
    def _detect_type(self, text: str) -> str:
        """Detect chunk type based on content patterns"""
        text_lower = text.lower().strip()
        
        # Heading patterns
        if len(text) < 100 and text.isupper():
            return "heading"
        
        # Clause patterns (e.g., "1.1", "Section 3")
        if re.match(r'^(\d+\.)+\d*\s', text) or re.match(r'^(section|article|clause)\s+\d+', text_lower):
            return "clause"
        
        # List item patterns
        if re.match(r'^[\-\•\*]\s', text) or re.match(r'^\([a-z]\)', text_lower):
            return "list_item"
        
        # Table row (simplified detection)
        if text.count('\t') >= 2:
            return "table_row"
        
        return "paragraph"
    
    def _extract_clause_number(self, text: str) -> Optional[str]:
        """Extract clause number like '3.2.1' or 'Section 5'"""
        # Match patterns like "1.2.3", "Section 5", "Article III"
        patterns = [
            r'^([\d]+(?:\.[\d]+)*)',  # 1.2.3
            r'^(Section\s+[\d]+)',     # Section 5
            r'^(Article\s+[IVX]+)',    # Article III
            r'^(Clause\s+[\d]+)',      # Clause 7
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
```

#### Embedding Generator

```python
from openai import AsyncOpenAI

class EmbeddingService:
    """Generate embeddings using OpenAI"""
    
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        
        # OpenAI batch limit is 2048
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch
            )
            
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.embed([text])
        return embeddings[0]
```

#### Document Classifier

```python
class DocumentClassifier:
    """Classify document type using LLM"""
    
    CLASSIFICATION_PROMPT = """
Analyze the following document excerpt and classify it.

Document excerpt (first 2000 characters):
{excerpt}

Provide classification in JSON format:
{{
    "document_type": "contract|brief|statute|case_law|medical_record|financial_statement|research_paper|report|correspondence|other",
    "confidence": 0.0-1.0,
    "structure": {{
        "has_toc": boolean,
        "section_count": number,
        "has_tables": boolean,
        "has_images": boolean
    }},
    "entities": ["list of key entities mentioned"],
    "dates_mentioned": ["YYYY-MM-DD format dates found"]
}}
"""
    
    async def classify(self, parsed_doc: ParsedDocument) -> dict:
        # Get first ~2000 chars for classification
        excerpt = self._get_excerpt(parsed_doc, max_chars=2000)
        
        prompt = self.CLASSIFICATION_PROMPT.format(excerpt=excerpt)
        
        response = await self.llm_client.complete(
            prompt,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.content)
```

#### Worker Process

```python
import asyncio
from aio_pika import connect_robust, IncomingMessage

class IngestionWorker:
    """Process document ingestion jobs from queue"""
    
    async def start(self):
        connection = await connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        
        queue = await channel.declare_queue(
            "document.process",
            durable=True
        )
        
        await queue.consume(self.process_message)
    
    async def process_message(self, message: IncomingMessage):
        async with message.process():
            try:
                data = json.loads(message.body)
                document_id = UUID(data["document_id"])
                
                await self.ingest_document(document_id)
                
            except Exception as e:
                logger.exception(f"Failed to process document: {e}")
                # Update status to failed
                await self.document_client.update_status(
                    document_id, 
                    "failed", 
                    str(e)
                )
    
    async def ingest_document(self, document_id: UUID):
        # 1. Get document info
        doc = await self.document_client.get_document(document_id)
        
        # 2. Download file from MinIO
        file_path = await self.storage.download_temp(doc.storage_path)
        
        try:
            # 3. Update status to processing
            await self.document_client.update_status(document_id, "processing")
            
            # 4. Parse document
            parser = ParserFactory.get_parser(doc.mime_type)
            parsed_doc = await parser.parse(file_path)
            
            # 5. Classify document
            classification = await self.classifier.classify(parsed_doc)
            
            # 6. Chunk document
            chunks = await self.chunker.chunk(parsed_doc)
            
            # 7. Generate embeddings
            embeddings = await self.embedding_service.embed(
                [chunk.content for chunk in chunks]
            )
            
            # 8. Store chunks with embeddings
            await self.store_chunks(document_id, chunks, embeddings)
            
            # 9. Update document with classification
            await self.document_client.update_classification(
                document_id,
                classification,
                page_count=len(parsed_doc.pages)
            )
            
            # 10. Update status to completed
            await self.document_client.update_status(document_id, "completed")
            
        finally:
            # Clean up temp file
            os.remove(file_path)
```

---

### 5.6 Workspace Service

**Technology**: Python FastAPI  
**Port**: 8085

#### Purpose
- Workspace CRUD
- Workspace document management
- Workspace member management
- Query session management
- Audit logging

#### API Endpoints

```python
# Workspace Service API

# ============ Templates ============

@router.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user)
) -> List[TemplateResponse]:
    """List available workspace templates"""
    pass

@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> TemplateDetailResponse:
    """Get template details including system prompt"""
    pass

# ============ Workspaces ============

@router.get("/workspaces")
async def list_workspaces(
    status: Optional[WorkspaceStatus] = None,
    template_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user)
) -> WorkspaceListResponse:
    """
    List workspaces.
    Returns only workspaces where user is a member.
    """
    pass

@router.post("/workspaces")
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    """
    Create a new workspace.
    Creator becomes owner.
    """
    pass

@router.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
) -> WorkspaceDetailResponse:
    """Get workspace details"""
    pass

@router.put("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    """Update workspace (admin+ only)"""
    pass

@router.post("/workspaces/{workspace_id}/archive")
async def archive_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    """Archive workspace (admin+ only)"""
    pass

@router.post("/workspaces/{workspace_id}/restore")
async def restore_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
) -> WorkspaceResponse:
    """Restore archived workspace"""
    pass

@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete workspace (owner only)"""
    pass

# ============ Workspace Documents ============

@router.get("/workspaces/{workspace_id}/documents")
async def list_workspace_documents(
    workspace_id: UUID,
    search: Optional[str] = None,
    document_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> WorkspaceDocumentListResponse:
    """List documents in workspace"""
    pass

@router.post("/workspaces/{workspace_id}/documents")
async def add_document_to_workspace(
    workspace_id: UUID,
    data: WorkspaceDocumentAdd,
    current_user: User = Depends(get_current_user)
) -> WorkspaceDocumentResponse:
    """Add existing document to workspace (member+ only)"""
    pass

@router.post("/workspaces/{workspace_id}/documents/batch")
async def add_documents_batch(
    workspace_id: UUID,
    data: WorkspaceDocumentAddBatch,
    current_user: User = Depends(get_current_user)
) -> List[WorkspaceDocumentResponse]:
    """Add multiple documents to workspace"""
    pass

@router.put("/workspaces/{workspace_id}/documents/{document_id}")
async def update_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    data: WorkspaceDocumentUpdate,
    current_user: User = Depends(get_current_user)
) -> WorkspaceDocumentResponse:
    """Update document notes/primary status"""
    pass

@router.delete("/workspaces/{workspace_id}/documents/{document_id}")
async def remove_document_from_workspace(
    workspace_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Remove document from workspace (admin+ only)"""
    pass

# ============ Workspace Members ============

@router.get("/workspaces/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[WorkspaceMemberResponse]:
    """List workspace members"""
    pass

@router.post("/workspaces/{workspace_id}/members")
async def add_workspace_member(
    workspace_id: UUID,
    data: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user)
) -> WorkspaceMemberResponse:
    """Add member to workspace (admin+ only)"""
    pass

@router.put("/workspaces/{workspace_id}/members/{user_id}")
async def update_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    data: WorkspaceMemberUpdate,
    current_user: User = Depends(get_current_user)
) -> WorkspaceMemberResponse:
    """Update member role (admin+ only)"""
    pass

@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Remove member from workspace (admin+ only)"""
    pass

# ============ Query Sessions ============

@router.get("/workspaces/{workspace_id}/sessions")
async def list_sessions(
    workspace_id: UUID,
    status: Optional[SessionStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> SessionListResponse:
    """List query sessions in workspace"""
    pass

@router.post("/workspaces/{workspace_id}/sessions")
async def create_session(
    workspace_id: UUID,
    data: SessionCreate,
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """Create new query session (member+ only)"""
    pass

@router.get("/workspaces/{workspace_id}/sessions/{session_id}")
async def get_session(
    workspace_id: UUID,
    session_id: UUID,
    include_messages: bool = Query(True),
    current_user: User = Depends(get_current_user)
) -> SessionDetailResponse:
    """Get session with messages"""
    pass

@router.put("/workspaces/{workspace_id}/sessions/{session_id}")
async def update_session(
    workspace_id: UUID,
    session_id: UUID,
    data: SessionUpdate,
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """Update session title/description/status"""
    pass

@router.delete("/workspaces/{workspace_id}/sessions/{session_id}")
async def delete_session(
    workspace_id: UUID,
    session_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete session"""
    pass

# ============ Audit ============

@router.get("/workspaces/{workspace_id}/audit")
async def get_workspace_audit_log(
    workspace_id: UUID,
    action: Optional[str] = None,
    user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> AuditLogListResponse:
    """Get workspace audit log (admin+ only)"""
    pass

# ============ Internal Endpoints ============

@router.get("/internal/workspaces/{workspace_id}")
async def internal_get_workspace(workspace_id: UUID) -> WorkspaceInternal:
    """Internal: Get workspace details"""
    pass

@router.get("/internal/workspaces/{workspace_id}/access")
async def internal_check_access(
    workspace_id: UUID,
    user_id: UUID
) -> AccessCheckResponse:
    """Internal: Check if user has access to workspace"""
    pass

@router.get("/internal/workspaces/{workspace_id}/documents")
async def internal_get_workspace_document_ids(
    workspace_id: UUID
) -> List[UUID]:
    """Internal: Get document IDs in workspace"""
    pass

@router.get("/internal/sessions/{session_id}")
async def internal_get_session(session_id: UUID) -> SessionInternal:
    """Internal: Get session details"""
    pass

@router.post("/internal/sessions/{session_id}/messages")
async def internal_add_message(
    session_id: UUID,
    data: MessageCreate
) -> MessageResponse:
    """Internal: Add message to session (from Query Service)"""
    pass
```

#### Models

```python
# Workspace models

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: str
    system_prompt_override: Optional[str] = None
    settings: Optional[dict] = None

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt_override: Optional[str] = None
    settings: Optional[dict] = None

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    template_id: str
    template_name: str
    status: str
    document_count: int
    member_count: int
    session_count: int
    created_by: UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime

class WorkspaceDetailResponse(WorkspaceResponse):
    system_prompt_override: Optional[str]
    settings: dict
    current_user_role: str  # The requesting user's role

class WorkspaceDocumentAdd(BaseModel):
    document_id: UUID
    notes: Optional[str] = None
    is_primary: bool = False

class WorkspaceMemberAdd(BaseModel):
    user_id: UUID
    role: WorkspaceRole = WorkspaceRole.MEMBER

class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    selected_document_ids: List[UUID] = []

class SessionDetailResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: Optional[str]
    description: Optional[str]
    selected_document_ids: List[UUID]
    selected_documents: List[DocumentSummary]
    status: str
    user_id: UUID
    user_name: str
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: List[Citation]
    created_at: datetime

class Citation(BaseModel):
    id: str  # e.g., "1", "2"
    document_id: UUID
    document_name: str
    chunk_id: UUID
    page_number: Optional[int]
    section: Optional[str]
    excerpt: str
    relevance_score: float
```

#### Permission Checking

```python
class WorkspacePermissionService:
    """Handle workspace permission checks"""
    
    ROLE_HIERARCHY = {
        WorkspaceRole.OWNER: 4,
        WorkspaceRole.ADMIN: 3,
        WorkspaceRole.MEMBER: 2,
        WorkspaceRole.VIEWER: 1,
    }
    
    PERMISSIONS = {
        "view": [WorkspaceRole.VIEWER, WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "query": [WorkspaceRole.VIEWER, WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "create_session": [WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "add_document": [WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "remove_document": [WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "manage_members": [WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "update_workspace": [WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
        "delete_workspace": [WorkspaceRole.OWNER],
        "view_audit": [WorkspaceRole.ADMIN, WorkspaceRole.OWNER],
    }
    
    async def get_user_role(
        self, 
        workspace_id: UUID, 
        user_id: UUID
    ) -> Optional[WorkspaceRole]:
        """Get user's role in workspace"""
        member = await self.member_repo.find_by_workspace_and_user(
            workspace_id, user_id
        )
        return member.role if member else None
    
    async def check_permission(
        self,
        workspace_id: UUID,
        user_id: UUID,
        permission: str
    ) -> bool:
        """Check if user has permission"""
        role = await self.get_user_role(workspace_id, user_id)
        if not role:
            return False
        
        allowed_roles = self.PERMISSIONS.get(permission, [])
        return role in allowed_roles
    
    async def require_permission(
        self,
        workspace_id: UUID,
        user_id: UUID,
        permission: str
    ) -> WorkspaceRole:
        """Check permission, raise if denied"""
        role = await self.get_user_role(workspace_id, user_id)
        
        if not role:
            raise HTTPException(404, "Workspace not found or access denied")
        
        allowed_roles = self.PERMISSIONS.get(permission, [])
        if role not in allowed_roles:
            raise HTTPException(403, f"Insufficient permissions for {permission}")
        
        return role
```

---

### 5.7 Query Service

**Technology**: Python FastAPI  
**Port**: 8086

#### Purpose
- Process user queries
- RAG retrieval (workspace-scoped)
- LLM interaction
- Citation generation and validation
- Conversation management

#### API Endpoints

```python
# Query Service API

@router.post("/query")
async def execute_query(
    data: QueryRequest,
    current_user: User = Depends(get_current_user)
) -> QueryResponse:
    """
    Execute a query in a workspace session.
    
    1. Verify workspace access
    2. Get session context
    3. Retrieve relevant chunks (workspace-scoped)
    4. Generate response with citations
    5. Store message
    6. Log audit event
    """
    pass

@router.post("/query/stream")
async def execute_query_stream(
    data: QueryRequest,
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    """Execute query with streaming response"""
    pass

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> MessageListResponse:
    """Get messages for a session"""
    pass

@router.get("/sessions/{session_id}/messages/{message_id}")
async def get_message(
    session_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user)
) -> MessageDetailResponse:
    """Get message details including full citations"""
    pass

@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
async def submit_feedback(
    session_id: UUID,
    message_id: UUID,
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user)
) -> None:
    """Submit feedback on a response (thumbs up/down)"""
    pass
```

#### Models

```python
class QueryRequest(BaseModel):
    workspace_id: UUID
    session_id: UUID
    question: str = Field(..., min_length=1, max_length=10000)
    selected_document_ids: Optional[List[UUID]] = None  # Override session selection
    
class QueryResponse(BaseModel):
    message_id: UUID
    content: str
    citations: List[Citation]
    sources_used: int
    model_used: str
    created_at: datetime

class Citation(BaseModel):
    id: str
    document_id: UUID
    document_name: str
    chunk_id: UUID
    page_number: Optional[int]
    section: Optional[str]
    section_hierarchy: List[str]
    excerpt: str
    relevance_score: float
```

#### Query Processor

```python
class QueryProcessor:
    """Main query processing pipeline"""
    
    def __init__(
        self,
        workspace_client: WorkspaceClient,
        document_client: DocumentClient,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        audit_client: AuditClient
    ):
        self.workspace_client = workspace_client
        self.document_client = document_client
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.audit_client = audit_client
    
    async def process(
        self,
        request: QueryRequest,
        user: User
    ) -> QueryResponse:
        
        # 1. Verify workspace access
        access = await self.workspace_client.check_access(
            request.workspace_id, 
            user.id
        )
        if not access.has_access:
            raise HTTPException(403, "Access denied to workspace")
        
        # 2. Get workspace and template
        workspace = await self.workspace_client.get_workspace(request.workspace_id)
        template = await self.workspace_client.get_template(workspace.template_id)
        
        # 3. Get session and document selection
        session = await self.workspace_client.get_session(request.session_id)
        doc_ids = request.selected_document_ids or session.selected_document_ids
        
        if not doc_ids:
            # If no documents selected, use all workspace documents
            doc_ids = await self.workspace_client.get_workspace_document_ids(
                request.workspace_id
            )
        
        if not doc_ids:
            raise HTTPException(400, "No documents available for querying")
        
        # 4. Generate query embedding
        query_embedding = await self.embedding_service.embed_single(request.question)
        
        # 5. Retrieve relevant chunks
        chunks = await self.document_client.search_chunks(
            document_ids=doc_ids,
            query_embedding=query_embedding,
            top_k=10,
            similarity_threshold=0.7
        )
        
        if not chunks:
            return self._create_no_sources_response(request.session_id)
        
        # 6. Build prompt with sources
        prompt = self._build_prompt(
            question=request.question,
            chunks=chunks,
            template=template,
            workspace=workspace
        )
        
        # 7. Get conversation history for context
        history = await self._get_conversation_history(request.session_id, limit=5)
        
        # 8. Call LLM
        llm_response = await self.llm_service.complete(
            prompt=prompt,
            history=history,
            settings=workspace.settings
        )
        
        # 9. Extract and validate citations
        content, citations = self._extract_citations(llm_response, chunks)
        
        # 10. Store user message
        user_message = await self.workspace_client.add_message(
            session_id=request.session_id,
            role="user",
            content=request.question
        )
        
        # 11. Store assistant message
        assistant_message = await self.workspace_client.add_message(
            session_id=request.session_id,
            role="assistant",
            content=content,
            citations=[c.dict() for c in citations],
            retrieved_chunks=[{"chunk_id": str(c.chunk_id), "score": c.similarity_score} for c in chunks],
            model_used=workspace.settings.get("default_model", "gpt-4o"),
            token_count_input=llm_response.input_tokens,
            token_count_output=llm_response.output_tokens,
            latency_ms=llm_response.latency_ms
        )
        
        # 12. Log audit
        await self.audit_client.log(
            organization_id=user.organization_id,
            workspace_id=request.workspace_id,
            user_id=user.id,
            action="query_executed",
            resource_type="session",
            resource_id=request.session_id,
            details={
                "message_id": str(assistant_message.id),
                "question_length": len(request.question),
                "documents_searched": len(doc_ids),
                "chunks_retrieved": len(chunks),
                "citations_generated": len(citations)
            }
        )
        
        # 13. Update usage
        await self._record_usage(user.organization_id, llm_response)
        
        return QueryResponse(
            message_id=assistant_message.id,
            content=content,
            citations=citations,
            sources_used=len(set(c.document_id for c in citations)),
            model_used=workspace.settings.get("default_model", "gpt-4o"),
            created_at=assistant_message.created_at
        )
    
    def _build_prompt(
        self,
        question: str,
        chunks: List[ChunkSearchResult],
        template: Template,
        workspace: Workspace
    ) -> str:
        """Build prompt with sources and instructions"""
        
        # Use override if set, otherwise template
        system_prompt = workspace.system_prompt_override or template.system_prompt
        output_instructions = template.output_instructions
        
        # Format sources
        sources_text = self._format_sources(chunks)
        
        prompt = f"""{system_prompt}

## Available Sources

{sources_text}

## Instructions

- Answer based ONLY on the provided sources
- Cite sources using [1], [2], etc. for each claim
- If information is not in the sources, clearly state that
- {output_instructions}

## Question

{question}
"""
        return prompt
    
    def _format_sources(self, chunks: List[ChunkSearchResult]) -> str:
        """Format chunks as numbered sources"""
        sources = []
        for i, chunk in enumerate(chunks, 1):
            location = f"Page {chunk.page_number}" if chunk.page_number else "Document"
            if chunk.section_title:
                location += f", {chunk.section_title}"
            
            source = f"""[{i}] {chunk.document_name}
Location: {location}
---
{chunk.content}
---
"""
            sources.append(source)
        return "\n".join(sources)
    
    def _extract_citations(
        self,
        llm_response: LLMResponse,
        chunks: List[ChunkSearchResult]
    ) -> Tuple[str, List[Citation]]:
        """Extract citation references from response"""
        
        content = llm_response.content
        citations = []
        
        # Find all [N] patterns
        citation_pattern = r'\[(\d+)\]'
        matches = re.findall(citation_pattern, content)
        
        seen = set()
        for match in matches:
            idx = int(match) - 1
            if idx < len(chunks) and match not in seen:
                chunk = chunks[idx]
                citations.append(Citation(
                    id=match,
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    section=chunk.section_title,
                    section_hierarchy=chunk.section_hierarchy,
                    excerpt=self._truncate(chunk.content, 200),
                    relevance_score=chunk.similarity_score
                ))
                seen.add(match)
        
        return content, citations
```

#### LLM Service

```python
class LLMService:
    """Handle LLM interactions"""
    
    def __init__(self, settings: Settings):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def complete(
        self,
        prompt: str,
        history: List[Message],
        settings: dict
    ) -> LLMResponse:
        
        model = settings.get("default_model", "gpt-4o")
        temperature = settings.get("temperature", 0.3)
        max_tokens = settings.get("max_tokens", 2000)
        
        start_time = time.time()
        
        # Build messages
        messages = []
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        messages.append({"role": "user", "content": prompt})
        
        if model.startswith("gpt"):
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
        elif model.startswith("claude"):
            response = await self.anthropic_client.messages.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=model
        )
```

---

### 5.8 Billing Service

**Technology**: Python FastAPI  
**Port**: 8087

#### Purpose
- Plan management
- Subscription lifecycle
- Usage tracking and limits
- Invoice generation
- Payment integration (Paystack, Flutterwave)

#### API Endpoints

```python
# Billing Service API

# ============ Plans ============

@router.get("/billing/plans")
async def list_plans() -> List[PlanResponse]:
    """List available plans"""
    pass

@router.get("/billing/plans/{plan_id}")
async def get_plan(plan_id: str) -> PlanDetailResponse:
    """Get plan details"""
    pass

# ============ Subscriptions ============

@router.get("/subscriptions/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """Get organization's current subscription"""
    pass

@router.post("/subscriptions")
async def create_subscription(
    data: SubscriptionCreate,
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """Create/upgrade subscription (admin only)"""
    pass

@router.post("/subscriptions/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """Cancel subscription at period end"""
    pass

@router.post("/subscriptions/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """Reactivate cancelled subscription"""
    pass

# ============ Usage ============

@router.get("/billing/usage")
async def get_current_usage(
    current_user: User = Depends(get_current_user)
) -> UsageResponse:
    """Get current period usage"""
    pass

@router.get("/billing/usage/history")
async def get_usage_history(
    months: int = Query(6, ge=1, le=12),
    current_user: User = Depends(get_current_user)
) -> List[UsageResponse]:
    """Get usage history"""
    pass

# ============ Invoices ============

@router.get("/billing/invoices")
async def list_invoices(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> InvoiceListResponse:
    """List invoices"""
    pass

@router.get("/billing/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user)
) -> InvoiceDetailResponse:
    """Get invoice details"""
    pass

@router.get("/billing/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """Download invoice as PDF"""
    pass

# ============ Payment ============

@router.post("/billing/payment/initialize")
async def initialize_payment(
    data: PaymentInitialize,
    current_user: User = Depends(get_current_user)
) -> PaymentInitResponse:
    """Initialize payment with provider"""
    pass

@router.post("/billing/webhooks/paystack")
async def paystack_webhook(request: Request) -> None:
    """Handle Paystack webhooks"""
    pass

# ============ Internal ============

@router.get("/internal/organizations/{org_id}/limits")
async def internal_get_limits(org_id: UUID) -> OrganizationLimits:
    """Internal: Get organization limits"""
    pass

@router.post("/internal/organizations/{org_id}/usage/increment")
async def internal_increment_usage(
    org_id: UUID,
    data: UsageIncrement
) -> None:
    """Internal: Increment usage counters"""
    pass

@router.get("/internal/organizations/{org_id}/can-perform")
async def internal_check_limit(
    org_id: UUID,
    action: str
) -> CanPerformResponse:
    """Internal: Check if action is within limits"""
    pass
```

#### Usage Tracking

```python
class UsageTracker:
    """Track and enforce usage limits"""
    
    async def get_current_usage(self, org_id: UUID) -> Usage:
        """Get current period usage"""
        
        # Get or create current period record
        period_start = self._get_period_start()
        
        record = await self.repo.get_or_create(
            org_id=org_id,
            period_start=period_start
        )
        
        return Usage(
            workspace_count=record.workspace_count,
            document_count=record.document_count,
            query_count=record.query_count,
            storage_bytes=record.storage_bytes,
            team_member_count=record.team_member_count,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens
        )
    
    async def get_limits(self, org_id: UUID) -> Limits:
        """Get organization limits from subscription"""
        
        subscription = await self.subscription_repo.get_active(org_id)
        if not subscription:
            # Return free tier limits
            return Limits.free_tier()
        
        plan = await self.plan_repo.get(subscription.plan_id)
        return Limits.from_plan(plan)
    
    async def can_perform(self, org_id: UUID, action: str) -> Tuple[bool, str]:
        """Check if organization can perform action within limits"""
        
        usage = await self.get_current_usage(org_id)
        limits = await self.get_limits(org_id)
        
        checks = {
            "create_workspace": (usage.workspace_count, limits.max_workspaces, "Workspace limit reached"),
            "upload_document": (usage.document_count, limits.max_documents, "Document limit reached"),
            "execute_query": (usage.query_count, limits.monthly_queries, "Query limit reached"),
            "add_member": (usage.team_member_count, limits.max_team_members, "Team member limit reached"),
        }
        
        if action not in checks:
            return True, ""
        
        current, limit, message = checks[action]
        
        # -1 means unlimited
        if limit == -1:
            return True, ""
        
        if current >= limit:
            return False, message
        
        return True, ""
    
    async def increment(
        self, 
        org_id: UUID, 
        **increments
    ) -> None:
        """Increment usage counters"""
        
        period_start = self._get_period_start()
        
        await self.repo.increment(
            org_id=org_id,
            period_start=period_start,
            **increments
        )
```

---

### 5.9 Notification Service

**Technology**: Python FastAPI  
**Port**: 8088

#### Purpose
- Email notifications
- In-app notifications
- Notification preferences

#### API Endpoints

```python
# Notification Service API

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user)
) -> NotificationListResponse:
    """List user's notifications"""
    pass

@router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user)
) -> UnreadCountResponse:
    """Get count of unread notifications"""
    pass

@router.post("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """Mark notification as read"""
    pass

@router.post("/notifications/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user)
) -> None:
    """Mark all notifications as read"""
    pass

# ============ Internal ============

@router.post("/internal/notifications/send")
async def internal_send_notification(
    data: NotificationSend
) -> None:
    """Internal: Send notification to user(s)"""
    pass

@router.post("/internal/email/send")
async def internal_send_email(
    data: EmailSend
) -> None:
    """Internal: Send email"""
    pass
```

#### Email Service
Use Brevo, Generate the service class



---

### 5.10 Export Service

**Technology**: Python FastAPI  
**Port**: 8089

#### Purpose
- Export query sessions as reports
- Export audit logs
- Generate PDF/DOCX documents

#### API Endpoints

```python
# Export Service API

@router.post("/exports/session/{session_id}")
async def export_session(
    session_id: UUID,
    format: str = Query("docx", regex="^(docx|pdf|md)$"),
    include_citations: bool = Query(True),
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """
    Export query session as a document.
    Includes all Q&A with citations.
    """
    pass

@router.post("/exports/workspace/{workspace_id}/audit")
async def export_audit_log(
    workspace_id: UUID,
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """Export workspace audit log"""
    pass

@router.get("/exports/{export_id}/status")
async def get_export_status(
    export_id: UUID,
    current_user: User = Depends(get_current_user)
) -> ExportStatusResponse:
    """Get status of async export job"""
    pass

@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """Download completed export"""
    pass
```

#### Report Generator

```python
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

class SessionReportGenerator:
    """Generate session reports in various formats"""
    
    async def generate_docx(
        self,
        session: SessionDetail,
        include_citations: bool = True
    ) -> bytes:
        """Generate DOCX report"""
        
        doc = Document()
        
        # Title
        title = doc.add_heading(session.title or "Query Session Report", 0)
        
        # Metadata
        doc.add_paragraph(f"Workspace: {session.workspace_name}")
        doc.add_paragraph(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}")
        doc.add_paragraph(f"Documents: {', '.join(d.name for d in session.selected_documents)}")
        
        doc.add_paragraph()  # Spacer
        
        # Q&A pairs
        for msg in session.messages:
            if msg.role == "user":
                p = doc.add_paragraph()
                p.add_run("Q: ").bold = True
                p.add_run(msg.content)
            
            elif msg.role == "assistant":
                p = doc.add_paragraph()
                p.add_run("A: ").bold = True
                p.add_run(msg.content)
                
                # Citations
                if include_citations and msg.citations:
                    doc.add_paragraph()
                    citations_para = doc.add_paragraph()
                    citations_para.add_run("Sources:").bold = True
                    
                    for citation in msg.citations:
                        source_text = f"\n[{citation.id}] {citation.document_name}"
                        if citation.page_number:
                            source_text += f", Page {citation.page_number}"
                        if citation.section:
                            source_text += f", {citation.section}"
                        citations_para.add_run(source_text)
                
                doc.add_paragraph()  # Spacer between Q&A pairs
        
        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
```

---

## 6. Infrastructure

### 6.1 Kubernetes Deployment

```yaml
# Example: workspace-service deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workspace-service
  namespace: chatcraft-professional
spec:
  replicas: 2
  selector:
    matchLabels:
      app: workspace-service
  template:
    metadata:
      labels:
        app: workspace-service
    spec:
      containers:
      - name: workspace-service
        image: gcr.io/PROJECT_ID/workspace-service:latest
        ports:
        - containerPort: 8085
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis_url
        livenessProbe:
          httpGet:
            path: /health
            port: 8085
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8085
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: workspace-service
  namespace: chatcraft-professional
spec:
  selector:
    app: workspace-service
  ports:
  - port: 8085
    targetPort: 8085
```

### 6.2 Resource Estimates

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas | Est. Monthly Cost |
|---------|-------------|-----------|----------------|--------------|----------|-------------------|
| API Gateway | 250m | 500m | 512Mi | 1Gi | 2 | $60 |
| Auth Service | 250m | 500m | 512Mi | 1Gi | 2 | $60 |
| Organization Service | 250m | 500m | 256Mi | 512Mi | 2 | $40 |
| Document Service | 250m | 500m | 512Mi | 1Gi | 2 | $60 |
| Ingestion Service | 500m | 1000m | 1Gi | 2Gi | 2 | $100 |
| Workspace Service | 250m | 500m | 256Mi | 512Mi | 2 | $40 |
| Query Service | 500m | 1000m | 512Mi | 1Gi | 2 | $80 |
| Billing Service | 250m | 500m | 256Mi | 512Mi | 2 | $40 |
| Notification Service | 250m | 500m | 256Mi | 512Mi | 1 | $20 |
| Export Service | 250m | 500m | 512Mi | 1Gi | 1 | $30 |
| PostgreSQL | 2000m | 4000m | 8Gi | 16Gi | 1 | $300 |
| Redis | 250m | 500m | 512Mi | 1Gi | 1 | $40 |
| MinIO | 500m | 1000m | 1Gi | 2Gi | 1 | $60 |
| RabbitMQ | 250m | 500m | 512Mi | 1Gi | 1 | $40 |
| **TOTAL** | | | | | | **~$970/mo** |

### 6.3 Network Architecture

```
                           ┌─────────────────┐
                           │  Cloud Load     │
                           │   Balancer      │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │  Ingress        │
                           │  (nginx)        │
                           └────────┬────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────┐
│                        K8s Cluster                                │
│                                                                   │
│  ┌──────────────┐     ┌──────────────────────────────────────-┐   │
│  │  Frontend    │     │         Service Mesh                  │   │
│  │  (React)     │     │                                       │   │
│  │  :3000       │◄────┤  Gateway ──► Auth ──► Organization    │   │
│  └──────────────┘     │     │                                 │   │
│                       │     ├────► Document ──► Ingestion     │   │
│                       │     │                                 │   │
│                       │     ├────► Workspace                  │   │
│                       │     │                                 │   │
│                       │     ├────► Query                      │   │
│                       │     │                                 │   │
│                       │     └────► Billing/Notification/Export│   │
│                       └──────────────────────────────────────-┘   │
│                                           │                       │
│                       ┌───────────────────┴───────────────────┐   │
│                       │           Data Layer                  │   │
│                       │  PostgreSQL │ Redis │ MinIO │ RabbitMQ│   │
│                       └───────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 7. Security

### 7.1 Authentication Flow

```
1. User Login
   Client → POST /api/v1/auth/login
         → Auth Service validates credentials
         → Returns access_token (15min) + refresh_token (7 days)

2. API Request
   Client → Any API endpoint with Authorization: Bearer <access_token>
         → Gateway extracts + validates JWT
         → Adds X-User-ID, X-Organization-ID headers
         → Forwards to service

3. Token Refresh
   Client → POST /api/v1/auth/refresh with refresh_token
         → Auth Service validates refresh token
         → Returns new access_token + refresh_token
```

### 7.2 Authorization Layers

```
Layer 1: Organization Isolation (Database RLS)
- All queries filtered by organization_id
- User can only see data from their organization

Layer 2: User Role (Organization Level)
- Owner: Full org control
- Admin: User management, billing
- Member: Standard access

Layer 3: Workspace Role
- Owner: Full workspace control
- Admin: Manage members, documents
- Member: Add documents, query
- Viewer: Read-only

Layer 4: Feature Access (Subscription)
- Plan determines available features
- Checked at API layer before allowing action
```

### 7.3 Data Encryption

| Data Type | At Rest | In Transit |
|-----------|---------|------------|
| User passwords | bcrypt hash | TLS 1.3 |
| Documents | AES-256 (MinIO SSE) | TLS 1.3 |
| Database | AES-256 (GCP managed) | TLS 1.3 |
| API tokens | SHA-256 hash | TLS 1.3 |

### 7.4 Secrets Management

```yaml
# All secrets stored in Google Secret Manager
secrets:
  - database-url
  - redis-url
  - minio-credentials
  - openai-api-key
  - anthropic-api-key
  - brevo-api-key
  - paystack-secret-key
  - jwt-signing-key
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)

**Week 1-2: Infrastructure & Core**
- [ ] Set up GKE cluster
- [ ] Deploy PostgreSQL, Redis, MinIO, RabbitMQ
- [ ] Create database schema
- [ ] Scaffold all service projects

**Week 3-4: Authentication & Organization**
- [ ] Auth Service: Registration, login, JWT
- [ ] Organization Service: Org CRUD, user management
- [ ] API Gateway: Routing, JWT validation
- [ ] Basic frontend: Login, registration

### Phase 2: Document Pipeline (Weeks 5-8)

**Week 5-6: Document Management**
- [ ] Document Service: Upload, list, metadata
- [ ] MinIO integration
- [ ] Document list UI

**Week 7-8: Ingestion**
- [ ] Ingestion Service: PDF, DOCX parsing
- [ ] Smart chunking with citations
- [ ] Embedding generation
- [ ] Document processing queue

### Phase 3: Workspaces & Query (Weeks 9-14)

**Week 9-10: Workspace Management**
- [ ] Workspace Service: CRUD, templates
- [ ] Workspace documents
- [ ] Workspace members
- [ ] Workspace UI

**Week 11-12: Query System**
- [ ] Query Service: RAG retrieval
- [ ] LLM integration
- [ ] Citation generation
- [ ] Query sessions

**Week 13-14: Query UI**
- [ ] Query interface
- [ ] Citation display
- [ ] Session management
- [ ] Document selection

### Phase 4: Billing & Polish (Weeks 15-18)

**Week 15-16: Billing**
- [ ] Billing Service: Plans, subscriptions
- [ ] Payment integration (Paystack)
- [ ] Usage tracking
- [ ] Billing UI

**Week 17-18: Polish**
- [ ] Export Service
- [ ] Notification Service
- [ ] Audit logging
- [ ] Performance optimization
- [ ] Bug fixes

### Phase 5: Launch Prep (Weeks 19-20)

- [ ] Security audit
- [ ] Load testing
- [ ] Documentation
- [ ] Beta testing
- [ ] Production deployment

---

## 9. Environment Configuration

### 9.1 Environment Variables

```bash
# ============ Common ============
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# ============ Database ============
DATABASE_URL=postgresql://user:pass@host:5432/chatcraft_professional
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# ============ Redis ============
REDIS_URL=redis://host:6379/0

# ============ MinIO ============
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
MINIO_BUCKET=chatcraft-professional
MINIO_SECURE=false

# ============ RabbitMQ ============
RABBITMQ_URL=amqp://user:pass@host:5672/

# ============ JWT ============
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ============ AI ============
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
DEFAULT_LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small

# ============ Email ============
BREVO_API_KEY=SG.xxx
FROM_EMAIL=noreply@chatcraft.cc

# ============ Payment ============
PAYSTACK_SECRET_KEY=sk_xxx
PAYSTACK_PUBLIC_KEY=pk_xxx

# ============ CORS ============
CORS_ORIGINS=https://app.chatcraft.cc,http://localhost:3000

# ============ Service URLs (for internal calls) ============
AUTH_SERVICE_URL=http://auth-service:8081
ORGANIZATION_SERVICE_URL=http://organization-service:8082
DOCUMENT_SERVICE_URL=http://document-service:8083
WORKSPACE_SERVICE_URL=http://workspace-service:8085
BILLING_SERVICE_URL=http://billing-service:8087
```

---

## 10. API Standards

### 10.1 Request/Response Format

```json
// Success Response
{
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_more": true
  }
}

// Error Response
{
  "error": {
    "code": "WORKSPACE_NOT_FOUND",
    "message": "Workspace not found or access denied",
    "details": { ... }
  }
}
```

### 10.2 Error Codes

```python
# Standard error codes
class ErrorCode:
    # Auth errors (AUTH_xxx)
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_TOKEN_INVALID = "AUTH_003"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_004"
    
    # Organization errors (ORG_xxx)
    ORG_NOT_FOUND = "ORG_001"
    ORG_USER_NOT_FOUND = "ORG_002"
    ORG_USER_ALREADY_EXISTS = "ORG_003"
    
    # Document errors (DOC_xxx)
    DOC_NOT_FOUND = "DOC_001"
    DOC_UPLOAD_FAILED = "DOC_002"
    DOC_PROCESSING_FAILED = "DOC_003"
    DOC_UNSUPPORTED_TYPE = "DOC_004"
    DOC_SIZE_EXCEEDED = "DOC_005"
    
    # Workspace errors (WS_xxx)
    WS_NOT_FOUND = "WS_001"
    WS_ACCESS_DENIED = "WS_002"
    WS_LIMIT_EXCEEDED = "WS_003"
    WS_DOCUMENT_NOT_IN_WORKSPACE = "WS_004"
    
    # Query errors (QUERY_xxx)
    QUERY_NO_DOCUMENTS = "QUERY_001"
    QUERY_LIMIT_EXCEEDED = "QUERY_002"
    QUERY_LLM_ERROR = "QUERY_003"
    
    # Billing errors (BILL_xxx)
    BILL_SUBSCRIPTION_NOT_FOUND = "BILL_001"
    BILL_PAYMENT_FAILED = "BILL_002"
    BILL_LIMIT_EXCEEDED = "BILL_003"
```

### 10.3 Pagination

```python
# Standard pagination parameters
page: int = Query(1, ge=1, description="Page number (1-indexed)")
page_size: int = Query(20, ge=1, le=100, description="Items per page")
sort_by: str = Query("created_at", description="Field to sort by")
sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction")
```

### 10.4 Versioning

- All APIs are versioned: `/api/v1/...`
- Breaking changes require new version
- Deprecation notice 3 months before removal

---

## Appendix A: Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Language | Python | AI/ML ecosystem, rapid development |
| Auth Service | Java Spring | Robust security, OAuth 2.0 support |
| API Framework | FastAPI | Async, auto-docs, Pydantic validation |
| Database | PostgreSQL | ACID, JSON support, pgvector |
| Vector Store | pgvector | Simplicity, no separate service |
| Cache | Redis | Industry standard, pub/sub support |
| Object Storage | MinIO | S3-compatible, self-hosted |
| Message Queue | RabbitMQ | Reliable, feature-rich |
| Cloud | GCP/GKE | Cost-effective, good K8s support |

---

*End of Specification*

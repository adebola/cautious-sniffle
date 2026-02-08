# ChatCraft Professional Backend

A document intelligence platform built as a microservices architecture, enabling organizations to upload documents, create workspaces, and query their document collections using AI-powered retrieval-augmented generation (RAG) with cited answers.

## Architecture Overview

The platform consists of **11 microservices** (2 Java/Spring Boot, 9 Python/FastAPI) organized in a monorepo, communicating via REST APIs and message queues.

```
                                    +------------------+
                                    |   Frontend App   |
                                    |  (Next.js/React) |
                                    +--------+---------+
                                             |
                                    +--------v---------+
                                    |  Gateway Service  |
                                    |   (Spring Cloud)  |
                                    |     :8080         |
                                    +--------+---------+
                                             |
                  +-----------+-----------+--+--+-----------+-----------+
                  |           |           |     |           |           |
          +-------v--+ +-----v----+ +----v---+ +----v---+ +v--------+ +v--------+
          |   Auth   | |   Org    | |  Doc   | |Workspace| | Query  | | Billing |
          | Service  | | Service  | |Service | |Service  | |Service | | Service |
          |  :8081   | |  :8082   | | :8083  | | :8085   | | :8086  | |  :8087  |
          +----------+ +----------+ +---+----+ +---------+ +--------+ +---------+
                                        |
                                   [RabbitMQ]
                                        |
                                  +-----v------+
                                  | Ingestion  |
                                  |  Service   |
                                  |   :8084    |
                                  +------------+

          +------------+  +---------------+  +-------------+
          |   Audit    |  | Notification  |  |   Export    |
          |  Service   |  |   Service     |  |  Service   |
          |   :8090    |  |    :8088      |  |   :8089    |
          +------------+  +---------------+  +-------------+
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Gateway** | Spring Cloud Gateway (Java 21) |
| **Auth** | Spring Authorization Server, OAuth 2.0 / OIDC, RSA JWT |
| **Python Services** | FastAPI, SQLAlchemy 2.0 async, Pydantic v2 |
| **Databases** | PostgreSQL 16 (per-service), MongoDB 7 (audit) |
| **Vector Search** | pgvector (cosine similarity, IVFFlat index) |
| **Object Storage** | MinIO (S3-compatible) |
| **Message Queue** | RabbitMQ (document processing pipeline) |
| **Cache** | Redis 7 |
| **AI/LLM** | OpenAI GPT-4o, Anthropic Claude (multi-provider) |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Payments** | Paystack (Nigerian Naira) |
| **Email** | Brevo (Sendinblue) with Jinja2 HTML templates |
| **Containerization** | Docker, Docker Compose |

## Microservices

### Authorization Service (Java, port 8081)

Handles user registration, login, JWT token issuance, and password management. Uses Spring Authorization Server for full OAuth 2.0/OIDC compliance with RSA-signed JWTs. Owns the `organizations` and `users` tables.

- `POST /api/v1/auth/register` - Register org + owner user
- `POST /api/v1/auth/login` - Authenticate and receive tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `GET /api/v1/auth/me` - Get current user profile

### Gateway Service (Java, port 8080)

Spring Cloud Gateway that validates JWTs via the Authorization Server's JWK Set endpoint and forwards identity headers (`X-User-ID`, `X-Organization-ID`, `X-User-Role`) to downstream services. Includes Redis-based rate limiting.

### Organization Service (Python, port 8082)

Manages organization settings, user invitations, and role-based user management. Proxies user/org CRUD to the Authorization Service.

- `GET/PUT /api/v1/organizations/current` - Org profile
- `GET /api/v1/organizations/current/usage` - Usage statistics
- `POST /api/v1/users/invite` - Invite user via email
- `POST /api/v1/users/invitations/accept` - Accept invitation
- `GET/POST/PUT/DELETE /api/v1/users/...` - User CRUD
- `PUT /api/v1/users/{id}/role` - Change user role (owner only)

### Document Service (Python, port 8083)

Handles document upload to MinIO, metadata storage, and vector chunk management with pgvector. Publishes processing events to RabbitMQ.

- `POST /api/v1/documents/` - Upload document
- `POST /api/v1/documents/batch` - Batch upload
- `GET /api/v1/documents/` - List documents (paginated, searchable)
- `GET /api/v1/documents/{id}/download` - Presigned download URL
- `POST /api/v1/documents/{id}/reprocess` - Re-trigger processing

### Ingestion Service (Python, port 8084)

Consumes the `document.process` RabbitMQ queue and runs the document processing pipeline:

1. Download from MinIO
2. Parse (PDF via PyMuPDF, DOCX via python-docx, XLSX via openpyxl)
3. Smart chunk with citation metadata (token-aware, sentence-boundary splitting)
4. Generate embeddings (OpenAI, batched)
5. Classify document type (LLM-based)
6. Store chunks with embeddings in pgvector

### Workspace Service (Python, port 8085)

Manages workspaces (created from templates), document collections, team members with role-based permissions, and query sessions.

- 6 built-in templates: Legal Matter, Medical Case, Audit Project, Research, Consulting, General
- Role hierarchy: Owner > Admin > Member > Viewer
- `POST /api/v1/workspaces/` - Create from template
- `POST /api/v1/workspaces/{id}/documents` - Add documents
- `POST /api/v1/workspaces/{id}/members` - Add members
- `POST /api/v1/workspaces/{id}/sessions` - Create query session

### Query Service (Python, port 8086)

The core RAG engine. Processes questions against workspace documents and returns cited answers.

1. Generate query embedding
2. Search document chunks via pgvector (cosine similarity)
3. Build prompt with numbered source references
4. Call LLM (GPT-4o or Claude, configurable per workspace)
5. Extract `[N]` citation markers and map to sources
6. Return answer with page/section citations

- `POST /api/v1/query/` - Ask question (JSON response)
- `POST /api/v1/query/stream` - Ask question (SSE streaming)

### Billing Service (Python, port 8087)

Manages subscription plans, usage tracking, limit enforcement, and Paystack payment processing.

- 3 plans: Starter (NGN 150K/mo), Growth (NGN 400K/mo), Enterprise (custom)
- Usage limits: workspaces, documents, queries, storage, team members
- `GET /api/v1/plans/` - List available plans
- `POST /api/v1/subscriptions/` - Create subscription
- `GET /api/v1/billing/usage/` - Current usage summary
- `GET /api/v1/billing/usage/can-perform/{action}` - Limit check

### Notification Service (Python, port 8088)

Handles in-app notifications and transactional email delivery via Brevo with Jinja2 HTML templates.

- `GET /api/v1/notifications` - List notifications
- `GET /api/v1/notifications/unread-count` - Unread count
- `POST /api/v1/notifications/read-all` - Mark all read
- Email templates: invitation, password reset, workspace added, document processed

### Export Service (Python, port 8089)

Exports query sessions and audit logs in multiple formats.

- `POST /api/v1/exports/sessions/{id}?format=docx` - Export session (DOCX, PDF, Markdown)
- `POST /api/v1/exports/audit?format=csv` - Export audit logs (CSV, XLSX)

### Audit Service (Python/MongoDB, port 8090)

Centralized audit trail backed by MongoDB. All services emit audit events via internal API. Supports TTL-based auto-expiry based on plan retention settings.

- `GET /api/v1/audit` - Query audit logs (admin/owner only)
- `GET /api/v1/audit/{id}` - Single audit entry

## Project Structure

```
chatcraft-backend/
├── pom.xml                          # Maven parent POM (Java modules)
├── docker-compose.yml               # Infrastructure (Postgres, Redis, MinIO, RabbitMQ, MongoDB)
├── docker-compose.services.yml      # All 11 application services
├── .env.example                     # Environment variables template
├── .gitignore
├── db/
│   └── init/
│       ├── 00-create-databases.sql  # Per-service database creation
│       └── 01-extensions.sql        # uuid-ossp, pgvector extensions
├── chatcraft-common/                # Shared Python library
│   └── chatcraft_common/
│       ├── auth.py                  # CurrentUser, get_current_user, require_role
│       ├── clients.py               # ServiceClient for inter-service HTTP calls
│       ├── database.py              # SQLAlchemy engine/session factory
│       ├── errors.py                # Error codes and exception classes
│       ├── health.py                # Health check router
│       ├── pagination.py            # PaginatedResponse, PaginationParams
│       └── settings.py              # BaseServiceSettings
├── authorization-service/           # Java Spring Boot
├── gateway-service/                 # Java Spring Cloud Gateway
├── organization-service/            # Python FastAPI
├── document-service/                # Python FastAPI
├── ingestion-service/               # Python FastAPI
├── workspace-service/               # Python FastAPI
├── query-service/                   # Python FastAPI
├── billing-service/                 # Python FastAPI
├── notification-service/            # Python FastAPI
├── export-service/                  # Python FastAPI
└── audit-service/                   # Python FastAPI + MongoDB
```

Each Python service follows a consistent internal structure:

```
service-name/
├── Dockerfile
├── requirements.txt
├── alembic.ini              # (not present in stateless services)
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
└── app/
    ├── __init__.py
    ├── main.py              # FastAPI app factory + lifespan
    ├── config.py            # Pydantic Settings
    ├── dependencies.py      # DI wiring
    ├── models/              # SQLAlchemy ORM models
    ├── schemas/             # Pydantic request/response schemas
    ├── repositories/        # Data access layer
    ├── services/            # Business logic
    └── routers/             # API endpoints (public + internal)
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Java 21 JDK (for local Java development)
- Python 3.12+ (for local Python development)
- OpenAI API key (for embeddings and LLM queries)

### Quick Start with Docker

1. Clone the repository and copy the environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set your API keys:

```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here    # Optional, for Claude support
PAYSTACK_SECRET_KEY=sk_test_your-key      # Optional, for payments
BREVO_API_KEY=xkeysib-your-key            # Optional, for email
```

3. Start everything:

```bash
# Infrastructure + all services
docker compose -f docker-compose.yml -f docker-compose.services.yml up --build
```

4. The API is available at `http://localhost:8080` (Gateway).

### Local Development

1. Start infrastructure only:

```bash
docker compose up -d
```

2. Install the shared Python library:

```bash
cd chatcraft-common && pip install -e . && cd ..
```

3. Run a Python service:

```bash
cd billing-service
pip install -r requirements.txt
python -m app.main
```

4. Run a Java service:

```bash
export JAVA_HOME=/path/to/jdk-21
./mvnw spring-boot:run -pl authorization-service
```

### Infrastructure Services

| Service | URL | Credentials |
|---------|-----|-------------|
| PostgreSQL | `localhost:5432` | `postgres` / `password` |
| Redis | `localhost:6379` | - |
| MinIO Console | `http://localhost:9001` | `minioadmin` / `minioadmin` |
| RabbitMQ Management | `http://localhost:15672` | `guest` / `guest` |
| MongoDB | `localhost:27017` | `mongo` / `password` |

## Authentication Flow

1. User registers via `POST /api/v1/auth/register` (creates organization + owner user)
2. User logs in via `POST /api/v1/auth/login` (receives JWT access + refresh tokens)
3. Client includes `Authorization: Bearer <token>` on all requests to the Gateway
4. Gateway validates JWT via the Authorization Server's JWK Set endpoint
5. Gateway extracts claims and forwards `X-User-ID`, `X-Organization-ID`, `X-User-Role` headers
6. Python services trust these headers (they are only reachable behind the Gateway)

## End-to-End Flow

```
Register Org -> Login -> Upload Document -> [Automatic Processing] ->
Create Workspace -> Add Document -> Create Session ->
Ask Question -> Receive Cited Answer -> Export Session
```

## Database Architecture

Each service owns its own database with no cross-service foreign keys. Services store UUIDs of external entities and resolve them via internal API calls.

| Database | Owner Service | Engine |
|----------|--------------|--------|
| `chatcraft_auth` | Authorization Service | PostgreSQL |
| `chatcraft_org` | Organization Service | PostgreSQL |
| `chatcraft_doc` | Document Service | PostgreSQL + pgvector |
| `chatcraft_workspace` | Workspace Service | PostgreSQL |
| `chatcraft_billing` | Billing Service | PostgreSQL |
| `chatcraft_notification` | Notification Service | PostgreSQL |
| `chatcraft_audit` | Audit Service | MongoDB |

## API Conventions

- All responses use a `{"data": ...}` envelope
- Paginated responses include `{"data": [...], "meta": {"page", "page_size", "total", "has_more"}}`
- Errors follow `{"error": {"code": "DOC_001", "message": "...", "details": {...}}}`
- Public endpoints: `/api/v1/...` (JWT required via Gateway)
- Internal endpoints: `/internal/...` (no auth, not exposed via Gateway)
- Health checks: `GET /health` on every service

## License

Proprietary - All rights reserved.

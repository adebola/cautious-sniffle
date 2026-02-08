"""Pydantic schemas for the Query Service."""

from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single citation referencing a document chunk used in the answer."""

    id: str = Field(..., description="Unique citation identifier")
    document_id: UUID = Field(..., description="ID of the source document")
    document_name: str = Field(..., description="Name of the source document")
    chunk_id: UUID = Field(..., description="ID of the referenced chunk")
    page_number: int | None = Field(None, description="Page number in the source document")
    section: str | None = Field(None, description="Section title in the source document")
    excerpt: str = Field(..., description="Relevant text excerpt from the chunk")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class QueryRequest(BaseModel):
    """Request to process a query against a workspace."""

    workspace_id: UUID = Field(..., description="Target workspace ID")
    session_id: UUID = Field(..., description="Conversation session ID")
    question: str = Field(..., min_length=1, max_length=10000, description="User question")
    stream: bool = Field(False, description="Whether to stream the response via SSE")
    model: str | None = Field(None, description="Override the default LLM model")


class TokenUsage(BaseModel):
    """Token usage statistics for a query."""

    input: int = Field(..., ge=0, description="Input tokens consumed")
    output: int = Field(..., ge=0, description="Output tokens generated")


class QueryResponse(BaseModel):
    """Complete response to a user query."""

    answer: str = Field(..., description="The LLM-generated answer")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    model_used: str = Field(..., description="LLM model that generated the response")
    token_usage: TokenUsage = Field(..., description="Token consumption")
    latency_ms: int = Field(..., ge=0, description="End-to-end latency in milliseconds")


class StreamEvent(BaseModel):
    """A single event in the SSE response stream."""

    event: str = Field(..., description="Event type: token, citations, done, error")
    data: str = Field(..., description="Event payload (token text, JSON, or empty)")

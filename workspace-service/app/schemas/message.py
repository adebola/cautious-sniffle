"""Message Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    citations: list[dict] = Field(default_factory=list)
    retrieved_chunks: list[dict] = Field(default_factory=list)
    model_used: str | None = None
    token_count_input: int | None = None
    token_count_output: int | None = None
    latency_ms: int | None = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[dict]
    model_used: str | None
    token_count_input: int | None
    token_count_output: int | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

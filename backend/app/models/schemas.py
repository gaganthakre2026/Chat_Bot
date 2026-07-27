from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    storage_path: str | None = None
    page_count: int = 0
    chunk_count: int | None = None
    status: Literal["processing", "ready", "failed"]
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RagHealthResponse(BaseModel):
    status: Literal["ok"]
    pipeline: str
    llm_provider: str
    embedding_dimensions: int
    steps: list[str]


class UploadResponse(BaseModel):
    document: DocumentOut


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: dict | None = None
    message: str | None = None


class LogoutResponse(BaseModel):
    ok: bool
    message: str


class RetrievedChunk(BaseModel):
    text: str
    page: int
    score: float


class ChatMessageIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    retrieved_chunks: list[RetrievedChunk]
    grounded: bool
    session_id: UUID


class MessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    confidence: float | None = None
    grounded: bool | None = True
    created_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str

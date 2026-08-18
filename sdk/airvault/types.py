"""Public types for the AirVault SDK."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SensitivityTier(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    @classmethod
    def _order(cls) -> list["SensitivityTier"]:
        return [cls.PUBLIC, cls.INTERNAL, cls.CONFIDENTIAL, cls.RESTRICTED]

    def allowed_tiers(self) -> list[str]:
        """Return tier values at or below this clearance level."""
        result = []
        for t in self._order():
            result.append(t.value)
            if t == self:
                break
        return result

    def __ge__(self, other: "SensitivityTier") -> bool:
        return self._order().index(self) >= self._order().index(other)

    def __gt__(self, other: "SensitivityTier") -> bool:
        return self._order().index(self) > self._order().index(other)


class FileType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"


# --- SDK Response Types ---


class Citation(BaseModel):
    """A single citation from a query result."""
    source: str
    page: int | None = None
    excerpt: str
    score: float
    sensitivity: SensitivityTier
    chunk_id: str


class QueryResult(BaseModel):
    """Result of a AirVault query."""
    answer: str
    citations: list[Citation]
    chunks_retrieved: int
    chunks_redacted: int
    query_time_ms: float


class IngestResult(BaseModel):
    """Result of a document ingestion."""
    id: UUID
    filename: str
    file_type: FileType
    chunk_count: int
    sensitivity: SensitivityTier
    status: str  # "completed" | "failed"
    error: str | None = None


class CollectionInfo(BaseModel):
    """Information about a document collection."""
    name: str
    description: str | None = None
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None


class DocumentInfo(BaseModel):
    """Metadata for an ingested document."""
    id: UUID
    filename: str
    file_type: FileType
    checksum: str
    collection_name: str
    sensitivity: SensitivityTier
    chunk_count: int
    file_size: int
    ingested_at: datetime


class HealthStatus(BaseModel):
    """Health check result."""
    status: str  # "ok" | "degraded"
    checks: dict[str, str]


class AuditEntry(BaseModel):
    """An entry in the audit log."""
    id: UUID
    user_id: str | None = None
    query_text: str
    collection_name: str | None = None
    user_clearance: SensitivityTier
    chunks_retrieved: int
    chunks_redacted: int
    response_summary: str | None = None
    query_duration_ms: float | None = None
    created_at: datetime


# --- Internal types ---


class ChunkData(BaseModel):
    """Internal: a chunk produced by the chunker."""
    content: str
    chunk_index: int
    page_number: int | None = None
    token_count: int = 0

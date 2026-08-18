from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SensitivityTier(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    @classmethod
    def order(cls) -> list["SensitivityTier"]:
        return [cls.PUBLIC, cls.INTERNAL, cls.CONFIDENTIAL, cls.RESTRICTED]

    def __ge__(self, other: "SensitivityTier") -> bool:
        return self.order().index(self) >= self.order().index(other)

    def __gt__(self, other: "SensitivityTier") -> bool:
        return self.order().index(self) > self.order().index(other)

    def __le__(self, other: "SensitivityTier") -> bool:
        return self.order().index(self) <= self.order().index(other)

    def __lt__(self, other: "SensitivityTier") -> bool:
        return self.order().index(self) < self.order().index(other)


class FileType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class IngestionJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    file_type: FileType
    checksum: str
    file_size: int
    collection_name: str = "default"
    status: JobStatus = JobStatus.QUEUED
    retry_count: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChunkData(BaseModel):
    content: str
    chunk_index: int
    page_number: int | None = None
    token_count: int = 0


class DocumentRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    file_type: FileType
    checksum: str
    collection_name: str
    sensitivity_tier: SensitivityTier = SensitivityTier.PUBLIC
    chunk_count: int = 0
    file_size: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

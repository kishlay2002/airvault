"""AirVault SDK error hierarchy.

All SDK errors inherit from AirVaultError so callers
can catch a single base class or specific subtypes.
"""


class AirVaultError(Exception):
    """Base exception for all AirVault SDK errors."""


class IngestionError(AirVaultError):
    """Raised when document ingestion fails (extraction, chunking, embedding, or storage)."""


class ExtractionError(IngestionError):
    """Raised when text extraction from a file fails."""


class UnsupportedFileTypeError(IngestionError):
    """Raised when the file type is not supported."""

    def __init__(self, extension: str, supported: list[str]):
        self.extension = extension
        self.supported = supported
        super().__init__(
            f"Unsupported file type: '{extension}'. Supported: {supported}"
        )


class DuplicateDocumentError(IngestionError):
    """Raised when a document with the same checksum already exists."""

    def __init__(self, checksum: str, existing_id: str | None = None):
        self.checksum = checksum
        self.existing_id = existing_id
        msg = f"Document with checksum {checksum[:16]}... already ingested"
        if existing_id:
            msg += f" (id={existing_id})"
        super().__init__(msg)


class RetrievalError(AirVaultError):
    """Raised when a query or retrieval operation fails."""


class CollectionNotFoundError(AirVaultError):
    """Raised when a referenced collection does not exist."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Collection '{name}' not found")


class ConfigurationError(AirVaultError):
    """Raised when the engine configuration is invalid."""


class StorageError(AirVaultError):
    """Raised when a storage backend (Qdrant/PostgreSQL) operation fails."""

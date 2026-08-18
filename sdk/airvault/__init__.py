"""AirVault — Air-Gapped Document Intelligence SDK

Usage:
    from airvault import AirVault, AirVaultConfig, SensitivityTier

    engine = AirVault()
    await engine.ingest("report.pdf", collection="hr")
    results = await engine.query("parental leave policy", clearance="internal")
"""

from airvault.config import AirVaultConfig
from airvault.engine import AirVault
from airvault.errors import (
    AirVaultError,
    IngestionError,
    ExtractionError,
    UnsupportedFileTypeError,
    DuplicateDocumentError,
    RetrievalError,
    CollectionNotFoundError,
    ConfigurationError,
    StorageError,
)
from airvault.sync import AirVaultSync
from airvault.types import (
    SensitivityTier,
    FileType,
    QueryResult,
    Citation,
    IngestResult,
    CollectionInfo,
    HealthStatus,
)

__all__ = [
    "AirVault",
    "AirVaultSync",
    "AirVaultConfig",
    # Types
    "SensitivityTier",
    "FileType",
    "QueryResult",
    "Citation",
    "IngestResult",
    "CollectionInfo",
    "HealthStatus",
    # Errors
    "AirVaultError",
    "IngestionError",
    "ExtractionError",
    "UnsupportedFileTypeError",
    "DuplicateDocumentError",
    "RetrievalError",
    "CollectionNotFoundError",
    "ConfigurationError",
    "StorageError",
]

__version__ = "0.1.0"

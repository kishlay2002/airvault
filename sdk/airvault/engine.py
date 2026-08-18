"""AirVault Engine — the main entry point for the SDK.

Usage:
    async with AirVault() as engine:
        await engine.ingest("report.pdf", collection="hr")
        results = await engine.query("parental leave policy", clearance="internal")

    # Or without context manager:
    engine = AirVault()
    await engine.ingest("report.pdf")
    await engine.close()
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from airvault.config import AirVaultConfig
from airvault.errors import (
    DuplicateDocumentError,
    IngestionError,
    UnsupportedFileTypeError,
    AirVaultError,
)
from airvault.types import (
    AuditEntry,
    CollectionInfo,
    DocumentInfo,
    FileType,
    HealthStatus,
    IngestResult,
    QueryResult,
    SensitivityTier,
)
from airvault.embedding.service import EmbeddingService
from airvault.ingestion.pipeline import IngestionPipeline
from airvault.retrieval.engine import RetrievalEngine
from airvault.storage.postgres import PostgresStore
from airvault.storage.qdrant import QdrantStore

logger = structlog.get_logger()

FILE_TYPE_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".txt": FileType.TEXT,
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".wav": FileType.AUDIO,
    ".mp3": FileType.AUDIO,
    ".flac": FileType.AUDIO,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".tiff": FileType.IMAGE,
    ".tif": FileType.IMAGE,
}


class AirVault:
    """Air-Gapped Document Intelligence Engine.

    The primary interface for ingesting documents, querying the knowledge base,
    and managing collections. All operations are async.

    Supports context manager for automatic resource cleanup:

        async with AirVault() as engine:
            await engine.ingest("report.pdf", collection="hr")
            results = await engine.query("leave policy", clearance="internal")
    """

    def __init__(self, config: AirVaultConfig | None = None):
        self.config = config or AirVaultConfig()
        self._setup_logging()

        # Core services (lazy-initialized)
        self._embedder: EmbeddingService | None = None
        self._qdrant: QdrantStore | None = None
        self._postgres: PostgresStore | None = None
        self._pipeline: IngestionPipeline | None = None
        self._retrieval: RetrievalEngine | None = None
        self._closed = False

        logger.info("airvault_initialized", model=self.config.embedding_model)

    async def __aenter__(self) -> "AirVault":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _setup_logging(self) -> None:
        import logging

        renderer = (
            structlog.processors.JSONRenderer()
            if self.config.log_format == "json"
            else structlog.dev.ConsoleRenderer()
        )
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                renderer,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
        )

    def _check_closed(self) -> None:
        if self._closed:
            raise AirVaultError("Engine is closed. Create a new AirVault instance.")

    @property
    def embedder(self) -> EmbeddingService:
        if self._embedder is None:
            self._embedder = EmbeddingService(
                model_name=self.config.embedding_model,
                dimension=self.config.embedding_dimension,
            )
        return self._embedder

    @property
    def qdrant(self) -> QdrantStore:
        if self._qdrant is None:
            self._qdrant = QdrantStore(
                host=self.config.qdrant_host,
                port=self.config.qdrant_port,
                dimension=self.config.embedding_dimension,
            )
        return self._qdrant

    @property
    def postgres(self) -> PostgresStore:
        if self._postgres is None:
            self._postgres = PostgresStore(dsn=self.config.postgres_dsn)
        return self._postgres

    @property
    def pipeline(self) -> IngestionPipeline:
        if self._pipeline is None:
            self._pipeline = IngestionPipeline(
                embedder=self.embedder,
                qdrant=self.qdrant,
                postgres=self.postgres,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                min_chunk_size=self.config.min_chunk_size,
                embedding_batch_size=self.config.embedding_batch_size,
            )
        return self._pipeline

    @property
    def retrieval(self) -> RetrievalEngine:
        if self._retrieval is None:
            self._retrieval = RetrievalEngine(
                embedder=self.embedder,
                qdrant=self.qdrant,
                postgres=self.postgres,
            )
        return self._retrieval

    # ── Ingestion ──────────────────────────────────────────────

    async def ingest(
        self,
        file_path: str | Path,
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
        metadata: dict | None = None,
    ) -> IngestResult:
        """Ingest a file into the knowledge base.

        Args:
            file_path: Path to the file (PDF, audio, image, text).
            collection: Target collection name (auto-created if missing).
            sensitivity: Manual sensitivity override. If None, auto-classified.
            metadata: Optional custom metadata to attach to the document.

        Returns:
            IngestResult with document ID, chunk count, and status.

        Raises:
            FileNotFoundError: If file_path does not exist.
            UnsupportedFileTypeError: If the file extension is not supported.
            DuplicateDocumentError: If a doc with the same checksum exists (when dedup is on).
            IngestionError: If extraction, chunking, or storage fails.
        """
        self._check_closed()

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        file_type = FILE_TYPE_MAP.get(ext)
        if file_type is None:
            raise UnsupportedFileTypeError(ext, list(FILE_TYPE_MAP.keys()))

        # Parse sensitivity
        tier_override = None
        if sensitivity is not None:
            tier_override = (
                SensitivityTier(sensitivity) if isinstance(sensitivity, str) else sensitivity
            )

        # Compute checksum
        content = path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()

        # Dedup check
        if self.config.dedup_enabled:
            existing = await self.postgres.find_by_checksum(checksum)
            if existing:
                raise DuplicateDocumentError(checksum, existing)

        logger.info(
            "ingestion_started",
            file=path.name,
            type=file_type.value,
            collection=collection,
            size=len(content),
        )

        try:
            result = await self.pipeline.process(
                file_path=path,
                file_type=file_type,
                collection=collection,
                checksum=checksum,
                file_size=len(content),
                sensitivity_override=tier_override,
                metadata=metadata,
            )
            logger.info(
                "ingestion_completed",
                file=path.name,
                chunks=result.chunk_count,
                sensitivity=result.sensitivity.value,
            )
            return result
        except (AirVaultError, FileNotFoundError):
            raise
        except Exception as e:
            logger.error("ingestion_failed", file=path.name, error=str(e))
            raise IngestionError(f"Failed to ingest {path.name}: {e}") from e

    async def ingest_batch(
        self,
        file_paths: list[str | Path],
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
    ) -> list[IngestResult]:
        """Ingest multiple files. Continues on individual failures.

        Args:
            file_paths: List of file paths.
            collection: Target collection.
            sensitivity: Optional manual sensitivity for all files.

        Returns:
            List of IngestResult, one per file. Failed files have status="failed".
        """
        self._check_closed()
        results = []
        for fp in file_paths:
            try:
                result = await self.ingest(fp, collection=collection, sensitivity=sensitivity)
                results.append(result)
            except (DuplicateDocumentError, IngestionError, UnsupportedFileTypeError) as e:
                logger.warning("batch_file_skipped", file=str(fp), error=str(e))
                results.append(IngestResult(
                    id=uuid4(), filename=Path(fp).name,
                    file_type=FILE_TYPE_MAP.get(Path(fp).suffix.lower(), FileType.TEXT),
                    chunk_count=0, sensitivity=SensitivityTier.PUBLIC,
                    status="failed", error=str(e),
                ))
        return results

    async def ingest_text(
        self,
        text: str,
        source_name: str = "inline_text",
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
    ) -> IngestResult:
        """Ingest raw text directly (no file needed).

        Args:
            text: The text content to ingest.
            source_name: A name for this text source.
            collection: Target collection.
            sensitivity: Optional manual sensitivity.

        Returns:
            IngestResult with document ID and chunk count.

        Raises:
            DuplicateDocumentError: If identical text already ingested.
            IngestionError: If chunking or storage fails.
        """
        self._check_closed()

        tier_override = None
        if sensitivity is not None:
            tier_override = (
                SensitivityTier(sensitivity) if isinstance(sensitivity, str) else sensitivity
            )

        checksum = hashlib.sha256(text.encode()).hexdigest()

        if self.config.dedup_enabled:
            existing = await self.postgres.find_by_checksum(checksum)
            if existing:
                raise DuplicateDocumentError(checksum, existing)

        try:
            return await self.pipeline.process_text(
                text=text,
                source_name=source_name,
                collection=collection,
                checksum=checksum,
                sensitivity_override=tier_override,
            )
        except AirVaultError:
            raise
        except Exception as e:
            raise IngestionError(f"Failed to ingest text '{source_name}': {e}") from e

    # ── Querying ───────────────────────────────────────────────

    async def query(
        self,
        text: str,
        collection: str = "default",
        clearance: SensitivityTier | str = SensitivityTier.PUBLIC,
        top_k: int | None = None,
        user_id: str | None = None,
    ) -> QueryResult:
        """Query the knowledge base with natural language.

        Access control is enforced at the vector retrieval boundary.
        Only chunks at or below the caller's clearance are returned.
        Restricted chunks are never loaded into application memory.

        Args:
            text: Natural language query.
            collection: Collection to search.
            clearance: Caller's clearance level (default: public).
            top_k: Number of results to return.
            user_id: Optional user ID for audit logging.

        Returns:
            QueryResult with answer, citations, and redaction count.
        """
        self._check_closed()

        if isinstance(clearance, str):
            clearance = SensitivityTier(clearance)

        k = min(top_k or self.config.default_top_k, self.config.max_top_k)

        return await self.retrieval.query(
            text=text,
            collection=collection,
            clearance=clearance,
            top_k=k,
            user_id=user_id,
        )

    # ── Collections ────────────────────────────────────────────

    async def list_collections(self) -> list[CollectionInfo]:
        """List all document collections."""
        self._check_closed()
        return await self.postgres.list_collections()

    async def create_collection(self, name: str, description: str | None = None) -> CollectionInfo:
        """Create a new collection."""
        self._check_closed()
        return await self.postgres.create_collection(name, description)

    async def delete_collection(self, name: str) -> None:
        """Delete a collection and all its documents."""
        self._check_closed()
        await self.postgres.delete_collection(name)
        try:
            self.qdrant.client.delete_collection(name)
        except Exception:
            pass

    async def collection_stats(self, name: str) -> CollectionInfo:
        """Get statistics for a collection."""
        self._check_closed()
        return await self.postgres.collection_stats(name)

    # ── Documents ──────────────────────────────────────────────

    async def list_documents(
        self,
        collection: str = "default",
        sensitivity: str | None = None,
        limit: int = 50,
    ) -> list[DocumentInfo]:
        """List documents in a collection."""
        self._check_closed()
        return await self.postgres.list_documents(collection, sensitivity, limit)

    async def get_document(self, doc_id: UUID) -> DocumentInfo | None:
        """Get metadata for a specific document."""
        self._check_closed()
        return await self.postgres.get_document(doc_id)

    async def delete_document(self, doc_id: UUID) -> None:
        """Delete a document and its vectors."""
        self._check_closed()
        await self.postgres.delete_document(doc_id)

    # ── Audit ──────────────────────────────────────────────────

    async def audit_log(
        self,
        username: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Query the audit log."""
        self._check_closed()
        return await self.postgres.query_audit_log(username, since, limit)

    # ── Health ─────────────────────────────────────────────────

    async def health(self) -> HealthStatus:
        """Check health of all dependencies."""
        checks: dict[str, str] = {}

        # PostgreSQL
        try:
            await self.postgres.ping()
            checks["postgres"] = "ok"
        except Exception as e:
            checks["postgres"] = f"error: {e}"

        # Qdrant
        try:
            self.qdrant.client.get_collections()
            checks["qdrant"] = "ok"
        except Exception as e:
            checks["qdrant"] = f"error: {e}"

        # Embedding model
        try:
            _ = self.embedder.model
            checks["embedding_model"] = "ok"
        except Exception as e:
            checks["embedding_model"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        return HealthStatus(status="ok" if all_ok else "degraded", checks=checks)

    # ── Lifecycle ──────────────────────────────────────────────

    async def close(self) -> None:
        """Clean up connections and resources. Safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        if self._postgres:
            await self._postgres.close()
        logger.info("airvault_closed")

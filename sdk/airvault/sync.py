"""Synchronous wrapper for AirVault engine.

For codebases that don't use async/await. Wraps every async method
in asyncio.run() for convenience.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from airvault.config import AirVaultConfig
from airvault.engine import AirVault
from airvault.types import (
    AuditEntry,
    CollectionInfo,
    DocumentInfo,
    HealthStatus,
    IngestResult,
    QueryResult,
    SensitivityTier,
)


class AirVaultSync:
    """Synchronous interface to the AirVault engine.

    Usage:
        engine = AirVaultSync()
        engine.ingest("report.pdf")
        results = engine.query("quarterly revenue", clearance="internal")
        engine.close()
    """

    def __init__(self, config: AirVaultConfig | None = None):
        self._engine = AirVault(config)

    def _run(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    # ── Ingestion ──

    def ingest(
        self,
        file_path: str | Path,
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
        metadata: dict | None = None,
    ) -> IngestResult:
        return self._run(
            self._engine.ingest(file_path, collection, sensitivity, metadata)
        )

    def ingest_batch(
        self,
        file_paths: list[str | Path],
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
    ) -> list[IngestResult]:
        return self._run(self._engine.ingest_batch(file_paths, collection, sensitivity))

    def ingest_text(
        self,
        text: str,
        source_name: str = "inline_text",
        collection: str = "default",
        sensitivity: SensitivityTier | str | None = None,
    ) -> IngestResult:
        return self._run(self._engine.ingest_text(text, source_name, collection, sensitivity))

    # ── Query ──

    def query(
        self,
        text: str,
        collection: str = "default",
        clearance: SensitivityTier | str = SensitivityTier.PUBLIC,
        top_k: int | None = None,
        user_id: str | None = None,
    ) -> QueryResult:
        return self._run(self._engine.query(text, collection, clearance, top_k, user_id))

    # ── Collections ──

    def list_collections(self) -> list[CollectionInfo]:
        return self._run(self._engine.list_collections())

    def create_collection(self, name: str, description: str | None = None) -> CollectionInfo:
        return self._run(self._engine.create_collection(name, description))

    def delete_collection(self, name: str) -> None:
        self._run(self._engine.delete_collection(name))

    def collection_stats(self, name: str) -> CollectionInfo:
        return self._run(self._engine.collection_stats(name))

    # ── Documents ──

    def list_documents(self, collection: str = "default", sensitivity: str | None = None, limit: int = 50) -> list[DocumentInfo]:
        return self._run(self._engine.list_documents(collection, sensitivity, limit))

    def get_document(self, doc_id: UUID) -> DocumentInfo | None:
        return self._run(self._engine.get_document(doc_id))

    def delete_document(self, doc_id: UUID) -> None:
        self._run(self._engine.delete_document(doc_id))

    # ── Audit ──

    def audit_log(self, username: str | None = None, since: str | None = None, limit: int = 50) -> list[AuditEntry]:
        return self._run(self._engine.audit_log(username, since, limit))

    # ── Health ──

    def health(self) -> HealthStatus:
        return self._run(self._engine.health())

    # ── Lifecycle ──

    def close(self) -> None:
        self._run(self._engine.close())

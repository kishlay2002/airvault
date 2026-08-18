"""PostgreSQL async storage for metadata, audit, and collections."""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from airvault.types import AuditEntry, CollectionInfo, DocumentInfo, SensitivityTier

logger = structlog.get_logger()


class PostgresStore:
    """Async PostgreSQL operations for AirVault metadata."""

    def __init__(self, dsn: str):
        self._engine = create_async_engine(dsn, pool_size=5, max_overflow=10)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _session(self) -> AsyncSession:
        return self._session_factory()

    async def ping(self) -> None:
        """Test database connectivity."""
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Dispose of the connection pool."""
        await self._engine.dispose()

    # ── Collections ────────────────────────────────────────────

    async def ensure_collection(self, name: str, description: str | None = None) -> str:
        """Ensure collection exists, return its ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("SELECT id FROM collections WHERE name = :name"), {"name": name}
            )
            row = result.fetchone()
            if row:
                return str(row[0])

            result = await session.execute(
                text(
                    "INSERT INTO collections (name, description) VALUES (:name, :desc) RETURNING id"
                ),
                {"name": name, "desc": description},
            )
            await session.commit()
            return str(result.fetchone()[0])

    async def list_collections(self) -> list[CollectionInfo]:
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT c.name, c.description, COUNT(d.id) AS doc_count,
                           COALESCE(SUM(d.chunk_count), 0) AS chunk_count, c.created_at
                    FROM collections c
                    LEFT JOIN documents d ON d.collection_id = c.id
                    GROUP BY c.name, c.description, c.created_at
                    ORDER BY c.created_at DESC
                """)
            )
            return [
                CollectionInfo(
                    name=r[0], description=r[1], document_count=r[2],
                    chunk_count=r[3], created_at=r[4],
                )
                for r in result.fetchall()
            ]

    async def create_collection(self, name: str, description: str | None = None) -> CollectionInfo:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO collections (name, description) VALUES (:name, :desc) "
                    "RETURNING name, description, created_at"
                ),
                {"name": name, "desc": description},
            )
            await session.commit()
            r = result.fetchone()
            return CollectionInfo(name=r[0], description=r[1], created_at=r[2])

    async def delete_collection(self, name: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("DELETE FROM collections WHERE name = :name"), {"name": name}
            )
            await session.commit()

    async def collection_stats(self, name: str) -> CollectionInfo:
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT c.name, c.description, COUNT(d.id), COALESCE(SUM(d.chunk_count), 0),
                           c.created_at
                    FROM collections c
                    LEFT JOIN documents d ON d.collection_id = c.id
                    WHERE c.name = :name
                    GROUP BY c.name, c.description, c.created_at
                """),
                {"name": name},
            )
            r = result.fetchone()
            if not r:
                raise ValueError(f"Collection '{name}' not found")
            return CollectionInfo(
                name=r[0], description=r[1], document_count=r[2],
                chunk_count=r[3], created_at=r[4],
            )

    # ── Dedup ──────────────────────────────────────────────────

    async def find_by_checksum(self, checksum: str) -> str | None:
        """Return document ID if a doc with this checksum exists, else None."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("SELECT id FROM documents WHERE checksum = :checksum"),
                {"checksum": checksum},
            )
            row = result.fetchone()
            return str(row[0]) if row else None

    # ── Documents ──────────────────────────────────────────────

    async def store_document(
        self, doc_id: UUID, filename: str, file_type: str, checksum: str,
        collection_id: str, sensitivity_tier: str, chunk_count: int, file_size: int,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO documents (id, filename, file_type, checksum, collection_id,
                                           sensitivity_tier, chunk_count, file_size)
                    VALUES (:id, :filename, :file_type, :checksum, :collection_id,
                            :sensitivity_tier, :chunk_count, :file_size)
                """),
                {
                    "id": str(doc_id), "filename": filename, "file_type": file_type,
                    "checksum": checksum, "collection_id": collection_id,
                    "sensitivity_tier": sensitivity_tier, "chunk_count": chunk_count,
                    "file_size": file_size,
                },
            )
            await session.commit()

    async def list_documents(
        self, collection: str, sensitivity: str | None = None, limit: int = 50
    ) -> list[DocumentInfo]:
        async with self._session_factory() as session:
            query = """
                SELECT d.id, d.filename, d.file_type, d.checksum, c.name,
                       d.sensitivity_tier, d.chunk_count, d.file_size, d.ingested_at
                FROM documents d JOIN collections c ON c.id = d.collection_id
                WHERE c.name = :collection
            """
            params: dict = {"collection": collection, "limit": limit}
            if sensitivity:
                query += " AND d.sensitivity_tier = :sensitivity"
                params["sensitivity"] = sensitivity
            query += " ORDER BY d.ingested_at DESC LIMIT :limit"

            result = await session.execute(text(query), params)
            return [
                DocumentInfo(
                    id=r[0], filename=r[1], file_type=r[2], checksum=r[3],
                    collection_name=r[4], sensitivity=r[5], chunk_count=r[6],
                    file_size=r[7], ingested_at=r[8],
                )
                for r in result.fetchall()
            ]

    async def get_document(self, doc_id: UUID) -> DocumentInfo | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT d.id, d.filename, d.file_type, d.checksum, c.name,
                           d.sensitivity_tier, d.chunk_count, d.file_size, d.ingested_at
                    FROM documents d JOIN collections c ON c.id = d.collection_id
                    WHERE d.id = :id
                """),
                {"id": str(doc_id)},
            )
            r = result.fetchone()
            if not r:
                return None
            return DocumentInfo(
                id=r[0], filename=r[1], file_type=r[2], checksum=r[3],
                collection_name=r[4], sensitivity=r[5], chunk_count=r[6],
                file_size=r[7], ingested_at=r[8],
            )

    async def delete_document(self, doc_id: UUID) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("DELETE FROM documents WHERE id = :id"), {"id": str(doc_id)}
            )
            await session.commit()

    # ── Audit ──────────────────────────────────────────────────

    async def log_audit(
        self, user_id: str | None, query_text: str, collection: str,
        clearance: str, retrieved: int, redacted: int,
        summary: str | None, duration_ms: float,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO audit_log (user_id, query_text, collection_name,
                        user_clearance, chunks_retrieved, chunks_redacted,
                        response_summary, query_duration_ms)
                    VALUES (:user_id, :query, :collection, :clearance,
                            :retrieved, :redacted, :summary, :duration_ms)
                """),
                {
                    "user_id": user_id, "query": query_text, "collection": collection,
                    "clearance": clearance, "retrieved": retrieved, "redacted": redacted,
                    "summary": summary, "duration_ms": duration_ms,
                },
            )
            await session.commit()

    async def query_audit_log(
        self, username: str | None = None, since: str | None = None, limit: int = 50
    ) -> list[AuditEntry]:
        async with self._session_factory() as session:
            query = """
                SELECT a.id, a.user_id, a.query_text, a.collection_name,
                       a.user_clearance, a.chunks_retrieved, a.chunks_redacted,
                       a.response_summary, a.query_duration_ms, a.created_at
                FROM audit_log a
            """
            conditions = []
            params: dict = {"limit": limit}

            if username:
                query += " JOIN users u ON u.id = a.user_id"
                conditions.append("u.username = :username")
                params["username"] = username
            if since:
                conditions.append("a.created_at >= :since")
                params["since"] = since

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY a.created_at DESC LIMIT :limit"

            result = await session.execute(text(query), params)
            return [
                AuditEntry(
                    id=r[0], user_id=str(r[1]) if r[1] else None,
                    query_text=r[2], collection_name=r[3],
                    user_clearance=r[4], chunks_retrieved=r[5], chunks_redacted=r[6],
                    response_summary=r[7], query_duration_ms=r[8], created_at=r[9],
                )
                for r in result.fetchall()
            ]

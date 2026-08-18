from uuid import UUID, uuid4

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models import ChunkData, DocumentRecord, SensitivityTier

logger = structlog.get_logger()


# --- Async PostgreSQL engine (singleton) ---
_engine = create_async_engine(settings.postgres_dsn, pool_size=5, max_overflow=10)
async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


# --- Qdrant Client (singleton) ---
_qdrant: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant


def ensure_collection(collection_name: str) -> None:
    """Create Qdrant collection if it doesn't exist."""
    client = get_qdrant()
    collections = [c.name for c in client.get_collections().collections]

    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info("qdrant_collection_created", collection=collection_name)


async def store_document(doc: DocumentRecord) -> None:
    """Insert document metadata into PostgreSQL."""
    async with async_session_factory() as session:
        # Resolve collection_id
        result = await session.execute(
            text("SELECT id FROM collections WHERE name = :name"),
            {"name": doc.collection_name},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Collection '{doc.collection_name}' not found")
        collection_id = row[0]

        await session.execute(
            text("""
                INSERT INTO documents (id, filename, file_type, checksum, collection_id,
                                       sensitivity_tier, chunk_count, file_size, ingested_at)
                VALUES (:id, :filename, :file_type, :checksum, :collection_id,
                        :sensitivity_tier, :chunk_count, :file_size, :ingested_at)
                ON CONFLICT (checksum) DO UPDATE SET
                    chunk_count = EXCLUDED.chunk_count,
                    sensitivity_tier = EXCLUDED.sensitivity_tier
            """),
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "file_type": doc.file_type.value,
                "checksum": doc.checksum,
                "collection_id": str(collection_id),
                "sensitivity_tier": doc.sensitivity_tier.value,
                "chunk_count": doc.chunk_count,
                "file_size": doc.file_size,
                "ingested_at": doc.ingested_at,
            },
        )
        await session.commit()
        logger.info("document_stored", document_id=str(doc.id), filename=doc.filename)


def store_vectors(
    collection_name: str,
    document_id: UUID,
    chunks: list[ChunkData],
    embeddings: list[list[float]],
    sensitivity_tier: SensitivityTier,
    source_file: str,
) -> list[str]:
    """Store chunk vectors in Qdrant with metadata payload."""
    client = get_qdrant()
    ensure_collection(collection_name)

    points: list[PointStruct] = []
    chunk_ids: list[str] = []

    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = str(uuid4())
        chunk_ids.append(chunk_id)

        points.append(
            PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "document_id": str(document_id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "token_count": chunk.token_count,
                    "sensitivity_tier": sensitivity_tier.value,
                    "collection_name": collection_name,
                    "source_file": source_file,
                },
            )
        )

    # Batch upsert (Qdrant handles batching internally)
    client.upsert(collection_name=collection_name, points=points)

    logger.info(
        "vectors_stored",
        collection=collection_name,
        document_id=str(document_id),
        count=len(points),
    )
    return chunk_ids


async def update_job_status(
    job_id: str, status: str, error_message: str | None = None
) -> None:
    """Update ingestion job status in PostgreSQL."""
    async with async_session_factory() as session:
        await session.execute(
            text("""
                UPDATE ingestion_jobs
                SET status = :status, error_message = :error_message, updated_at = now()
                WHERE id = :job_id
            """),
            {"job_id": job_id, "status": status, "error_message": error_message},
        )
        await session.commit()


async def create_job_record(
    job_id: str,
    file_path: str,
    file_type: str,
    checksum: str,
    file_size: int,
    collection_name: str,
) -> None:
    """Create an ingestion job record in PostgreSQL."""
    async with async_session_factory() as session:
        # Resolve collection_id
        result = await session.execute(
            text("SELECT id FROM collections WHERE name = :name"),
            {"name": collection_name},
        )
        row = result.fetchone()
        collection_id = str(row[0]) if row else None

        await session.execute(
            text("""
                INSERT INTO ingestion_jobs (id, file_path, file_type, checksum, file_size,
                                            collection_id, status)
                VALUES (:id, :file_path, :file_type, :checksum, :file_size,
                        :collection_id, 'processing')
            """),
            {
                "id": job_id,
                "file_path": file_path,
                "file_type": file_type,
                "checksum": checksum,
                "file_size": file_size,
                "collection_id": collection_id,
            },
        )
        await session.commit()

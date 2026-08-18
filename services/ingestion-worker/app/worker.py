"""VaultMind Ingestion Worker

Consumes jobs from Redis queue via arq, processes files through the
extraction → chunking → embedding → classification → storage pipeline.
"""

import os
import traceback

import structlog
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from app.config import settings
from app.models import FileType, DocumentRecord, SensitivityTier, JobStatus
from app.extractors import get_extractor
from app.chunker import RecursiveChunker
from app.classifier import SensitivityClassifier
from app.embedder import EmbeddingService
from app.store import (
    store_document,
    store_vectors,
    update_job_status,
    create_job_record,
)

logger = structlog.get_logger()

# Shared instances (initialized once per worker process)
chunker = RecursiveChunker()
classifier = SensitivityClassifier()


async def process_ingestion_job(
    ctx: dict,
    job_id: str,
    file_path: str,
    file_type: str,
    checksum: str,
    file_size: int,
    collection_name: str = "default",
) -> dict:
    """Main ingestion pipeline: Extract → Chunk → Embed → Classify → Store.

    Args:
        ctx: arq worker context.
        job_id: Unique job identifier.
        file_path: Absolute path to the file.
        file_type: File type string (pdf, audio, image, text, markdown).
        checksum: SHA-256 checksum of the file.
        file_size: File size in bytes.
        collection_name: Target collection name.

    Returns:
        dict with ingestion results.
    """
    log = logger.bind(job_id=job_id, file_path=file_path, file_type=file_type)
    log.info("ingestion_started")

    try:
        # Record job in DB
        await create_job_record(job_id, file_path, file_type, checksum, file_size, collection_name)

        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ft = FileType(file_type)

        # Step 1: Extract text
        extractor = get_extractor(ft)
        extraction = await extractor.extract(file_path)
        log.info("extraction_complete", chars=len(extraction.text))

        if not extraction.text.strip():
            raise ValueError("Extraction produced empty text")

        # Step 2: Chunk text
        chunks = chunker.chunk_text(extraction.text, extraction.page_texts)
        log.info("chunking_complete", chunks=len(chunks))

        if not chunks:
            raise ValueError("Chunking produced zero chunks")

        # Step 3: Classify sensitivity
        tier = classifier.classify(extraction.text)
        log.info("classification_complete", tier=tier.value)

        # Step 4: Generate embeddings
        embedder = EmbeddingService.get_instance()
        chunk_texts = [c.content for c in chunks]
        embeddings = embedder.embed(chunk_texts)
        log.info("embedding_complete", vectors=len(embeddings))

        # Step 5: Store document record
        filename = os.path.basename(file_path)
        doc = DocumentRecord(
            filename=filename,
            file_type=ft,
            checksum=checksum,
            collection_name=collection_name,
            sensitivity_tier=tier,
            chunk_count=len(chunks),
            file_size=file_size,
        )
        await store_document(doc)

        # Step 6: Store vectors in Qdrant
        chunk_ids = store_vectors(
            collection_name=collection_name,
            document_id=doc.id,
            chunks=chunks,
            embeddings=embeddings,
            sensitivity_tier=tier,
            source_file=filename,
        )

        # Step 7: Mark job complete
        await update_job_status(job_id, JobStatus.COMPLETED.value)

        result = {
            "job_id": job_id,
            "document_id": str(doc.id),
            "filename": filename,
            "chunks": len(chunks),
            "sensitivity_tier": tier.value,
            "status": "completed",
        }
        log.info("ingestion_completed", **result)
        return result

    except Exception as e:
        log.error("ingestion_failed", error=str(e), traceback=traceback.format_exc())

        # Check retry count from context
        job_try = ctx.get("job_try", 1)
        if job_try >= settings.max_retries:
            await update_job_status(job_id, JobStatus.DEAD_LETTER.value, str(e))
            log.error("job_dead_lettered", retries=job_try)
        else:
            await update_job_status(job_id, JobStatus.FAILED.value, str(e))
            raise  # arq will retry

        return {"job_id": job_id, "status": "dead_letter", "error": str(e)}


async def startup(ctx: dict) -> None:
    """Worker startup: pre-load embedding model."""
    logger.info("worker_starting")
    EmbeddingService.get_instance()
    logger.info("worker_ready")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown."""
    logger.info("worker_shutting_down")


class WorkerSettings:
    """arq worker configuration."""

    functions = [process_ingestion_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
    job_timeout = 600  # 10 minutes per job
    retry_jobs = True
    max_tries = settings.max_retries
    health_check_interval = 30

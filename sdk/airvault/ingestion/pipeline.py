"""Ingestion pipeline — orchestrates extract → chunk → classify → embed → store."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import structlog

from airvault.embedding.service import EmbeddingService
from airvault.ingestion.chunker import RecursiveChunker
from airvault.ingestion.classifier import SensitivityClassifier
from airvault.ingestion.extractors import get_extractor
from airvault.storage.postgres import PostgresStore
from airvault.storage.qdrant import QdrantStore
from airvault.types import FileType, IngestResult, SensitivityTier

logger = structlog.get_logger()


class IngestionPipeline:
    """End-to-end document ingestion pipeline.

    Extracts text from files, chunks it, classifies sensitivity,
    generates embeddings, and stores in Qdrant + PostgreSQL.
    """

    def __init__(
        self,
        embedder: EmbeddingService,
        qdrant: QdrantStore,
        postgres: PostgresStore,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 50,
        embedding_batch_size: int = 64,
    ):
        self.embedder = embedder
        self.qdrant = qdrant
        self.postgres = postgres
        self.chunker = RecursiveChunker(chunk_size, chunk_overlap, min_chunk_size)
        self.classifier = SensitivityClassifier()
        self.embedding_batch_size = embedding_batch_size

    async def process(
        self,
        file_path: Path,
        file_type: FileType,
        collection: str,
        checksum: str,
        file_size: int,
        sensitivity_override: SensitivityTier | None = None,
        metadata: dict | None = None,
    ) -> IngestResult:
        """Process a file through the full ingestion pipeline.

        Steps: extract → chunk → classify → embed → store
        """
        doc_id = uuid4()

        # 1. Extract text
        extractor = get_extractor(file_type)
        extraction = extractor.extract(file_path)

        if not extraction.text and not extraction.page_texts:
            raise ValueError(f"No text extracted from {file_path.name}")

        # 2. Chunk
        chunks = self.chunker.chunk_text(
            text=extraction.text,
            page_texts=extraction.page_texts or None,
        )

        if not chunks:
            raise ValueError(f"No chunks produced from {file_path.name}")

        # 3. Classify sensitivity
        full_text = extraction.text or " ".join(extraction.page_texts)
        if sensitivity_override:
            doc_sensitivity = sensitivity_override
        else:
            doc_sensitivity = self.classifier.classify(full_text)

        # 4. Embed all chunks (batched to prevent OOM on large docs)
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_batched(chunk_texts, batch_size=self.embedding_batch_size)

        # 5. Ensure Qdrant collection exists
        self.qdrant.ensure_collection(collection)

        # 6. Ensure DB collection exists
        collection_id = await self.postgres.ensure_collection(collection)

        # 7. Store document metadata in PostgreSQL
        await self.postgres.store_document(
            doc_id=doc_id,
            filename=file_path.name,
            file_type=file_type.value,
            checksum=checksum,
            collection_id=collection_id,
            sensitivity_tier=doc_sensitivity.value,
            chunk_count=len(chunks),
            file_size=file_size,
        )

        # 8. Store vectors in Qdrant
        self.qdrant.store_vectors(
            collection_name=collection,
            doc_id=str(doc_id),
            chunks=chunks,
            embeddings=embeddings,
            sensitivity_tier=doc_sensitivity.value,
            source_file=file_path.name,
            metadata=metadata,
        )

        logger.info(
            "pipeline_completed",
            doc_id=str(doc_id),
            file=file_path.name,
            chunks=len(chunks),
            sensitivity=doc_sensitivity.value,
        )

        return IngestResult(
            id=doc_id,
            filename=file_path.name,
            file_type=file_type,
            chunk_count=len(chunks),
            sensitivity=doc_sensitivity,
            status="completed",
        )

    async def process_text(
        self,
        text: str,
        source_name: str,
        collection: str,
        checksum: str,
        sensitivity_override: SensitivityTier | None = None,
    ) -> IngestResult:
        """Process raw text (no file) through the pipeline."""
        doc_id = uuid4()

        # Chunk
        chunks = self.chunker.chunk_text(text=text)
        if not chunks:
            raise ValueError("No chunks produced from input text")

        # Classify
        doc_sensitivity = sensitivity_override or self.classifier.classify(text)

        # Embed (batched)
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_batched(chunk_texts, batch_size=self.embedding_batch_size)

        # Store
        self.qdrant.ensure_collection(collection)
        collection_id = await self.postgres.ensure_collection(collection)

        await self.postgres.store_document(
            doc_id=doc_id,
            filename=source_name,
            file_type="text",
            checksum=checksum,
            collection_id=collection_id,
            sensitivity_tier=doc_sensitivity.value,
            chunk_count=len(chunks),
            file_size=len(text.encode()),
        )

        self.qdrant.store_vectors(
            collection_name=collection,
            doc_id=str(doc_id),
            chunks=chunks,
            embeddings=embeddings,
            sensitivity_tier=doc_sensitivity.value,
            source_file=source_name,
        )

        return IngestResult(
            id=doc_id,
            filename=source_name,
            file_type=FileType.TEXT,
            chunk_count=len(chunks),
            sensitivity=doc_sensitivity,
            status="completed",
        )

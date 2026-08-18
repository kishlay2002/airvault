"""Qdrant vector storage wrapper."""

from uuid import uuid4

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchAny,
    PointStruct,
    VectorParams,
)

from airvault.types import ChunkData

logger = structlog.get_logger()


class QdrantStore:
    """Manages vector storage in Qdrant."""

    def __init__(self, host: str = "localhost", port: int = 6333, dimension: int = 384):
        self.client = QdrantClient(host=host, port=port)
        self.dimension = dimension
        self._initialized_collections: set[str] = set()

    def ensure_collection(self, name: str) -> None:
        """Create collection if it doesn't exist."""
        if name in self._initialized_collections:
            return

        existing = [c.name for c in self.client.get_collections().collections]
        if name not in existing:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=name)

        self._initialized_collections.add(name)

    def store_vectors(
        self,
        collection_name: str,
        doc_id: str,
        chunks: list[ChunkData],
        embeddings: list[list[float]],
        sensitivity_tier: str,
        source_file: str,
        metadata: dict | None = None,
    ) -> None:
        """Store chunk embeddings with payload in Qdrant."""
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "document_id": doc_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "sensitivity_tier": sensitivity_tier,
                "source_file": source_file,
                "collection_name": collection_name,
            }
            if metadata:
                payload["custom_metadata"] = metadata

            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=embedding,
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=collection_name, points=points)
        logger.info("vectors_stored", collection=collection_name, count=len(points))

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        query_filter: Filter | None = None,
        limit: int = 5,
    ) -> list:
        """Search for similar vectors with optional filter."""
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    def count(self, collection_name: str, count_filter: Filter | None = None) -> int:
        """Count points matching a filter without loading payloads."""
        result = self.client.count(
            collection_name=collection_name,
            count_filter=count_filter,
            exact=True,
        )
        return result.count

    def scroll(self, collection_name: str, scroll_filter: Filter, limit: int = 100) -> list:
        """Scroll through points matching a filter."""
        result = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
        )
        return result[0]  # return points, discard next_page_offset

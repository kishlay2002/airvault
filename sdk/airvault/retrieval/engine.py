"""Query retrieval engine with compliance-aware access filtering."""

from __future__ import annotations

import time

import structlog

from airvault.embedding.service import EmbeddingService
from airvault.retrieval.access import build_access_filter, build_redaction_filter
from airvault.storage.postgres import PostgresStore
from airvault.storage.qdrant import QdrantStore
from airvault.types import Citation, QueryResult, SensitivityTier

logger = structlog.get_logger()


class RetrievalEngine:
    """Executes queries with compliance-aware access control.

    The access filter is applied at the Qdrant query level (pre-retrieval),
    so restricted chunks are never loaded into application memory.
    """

    def __init__(
        self,
        embedder: EmbeddingService,
        qdrant: QdrantStore,
        postgres: PostgresStore,
    ):
        self.embedder = embedder
        self.qdrant = qdrant
        self.postgres = postgres

    async def query(
        self,
        text: str,
        collection: str,
        clearance: SensitivityTier,
        top_k: int = 5,
        user_id: str | None = None,
    ) -> QueryResult:
        """Execute a query with access control and audit logging.

        Steps:
            1. Embed the query
            2. Build access filter from clearance level
            3. Search Qdrant with filter (pre-retrieval filtering)
            4. Count redacted chunks via metadata filter (never loads content)
            5. Build extractive answer from top citations
            6. Log audit trail
        """
        start = time.monotonic()

        # 1. Embed
        query_vector = self.embedder.embed_query(text)

        # 2. Access filter
        access_filter = build_access_filter(clearance)

        # 3. Filtered search — only allowed chunks are returned
        filtered = self.qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=access_filter,
            limit=top_k,
        )

        # 4. Count redacted chunks using an inverted filter (never loads content)
        redaction_filter = build_redaction_filter(clearance)
        redacted = 0
        if redaction_filter is not None:
            redacted = self.qdrant.count(collection_name=collection, count_filter=redaction_filter)

        # 5. Build citations
        citations: list[Citation] = []
        for result in filtered:
            payload = result.payload or {}
            citations.append(
                Citation(
                    source=payload.get("source_file", "unknown"),
                    page=payload.get("page_number"),
                    excerpt=payload.get("content", "")[:500],
                    score=round(result.score, 4),
                    sensitivity=SensitivityTier(payload.get("sensitivity_tier", "public")),
                    chunk_id=str(result.id),
                )
            )

        # 6. Build extractive answer
        answer = self._extractive_answer(citations)

        elapsed_ms = (time.monotonic() - start) * 1000

        # 7. Audit log
        try:
            await self.postgres.log_audit(
                user_id=user_id,
                query_text=text,
                collection=collection,
                clearance=clearance.value,
                retrieved=len(citations),
                redacted=redacted,
                summary=answer[:500] if answer else None,
                duration_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            logger.warning("audit_log_failed", error=str(e))

        logger.info(
            "query_completed",
            collection=collection,
            clearance=clearance.value,
            retrieved=len(citations),
            redacted=redacted,
            duration_ms=round(elapsed_ms, 2),
        )

        return QueryResult(
            answer=answer,
            citations=citations,
            chunks_retrieved=len(citations),
            chunks_redacted=redacted,
            query_time_ms=round(elapsed_ms, 2),
        )

    def _extractive_answer(self, citations: list[Citation]) -> str:
        """Build an extractive answer from top citations."""
        if not citations:
            return "No relevant documents found for your query."

        parts = [f"Based on {len(citations)} relevant document(s):\n"]
        for i, c in enumerate(citations[:3], 1):
            source = f"[{c.source}"
            if c.page:
                source += f", p.{c.page}"
            source += f"] (score: {c.score})"
            parts.append(f"{i}. {source}\n   {c.excerpt[:300]}...")

        return "\n\n".join(parts)

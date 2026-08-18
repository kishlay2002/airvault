import time

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.config import settings
from app.models.common import SensitivityTier
from app.models.query import Citation, QueryRequest, QueryResponse
from app.services.embedding import EmbeddingService

logger = structlog.get_logger()

_qdrant: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant


def build_access_filter(user_clearance: SensitivityTier) -> Filter:
    """Build Qdrant filter that only returns chunks at or below user's clearance."""
    allowed = user_clearance.allowed_tiers()
    return Filter(
        must=[
            FieldCondition(
                key="sensitivity_tier",
                match=MatchAny(any=allowed),
            )
        ]
    )


class RetrievalService:
    def __init__(self):
        self.qdrant = get_qdrant()
        self.embedder = EmbeddingService.get_instance()

    async def query(
        self,
        request: QueryRequest,
        user_clearance: SensitivityTier,
        user_id: str,
    ) -> QueryResponse:
        start = time.monotonic()

        # 1. Embed query
        query_vector = self.embedder.embed_query(request.query)

        # 2. Build access filter
        access_filter = build_access_filter(user_clearance)

        # 3. Search Qdrant with access filter
        filtered_results = self.qdrant.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            query_filter=access_filter,
            limit=request.top_k,
            with_payload=True,
        )

        # 4. Search without filter to count redacted chunks
        unfiltered_results = self.qdrant.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            limit=request.top_k,
            with_payload=True,
        )
        chunks_redacted = len(unfiltered_results) - len(filtered_results)

        # 5. Build citations
        citations: list[Citation] = []
        for result in filtered_results:
            payload = result.payload or {}
            citations.append(
                Citation(
                    document_name=payload.get("source_file", "unknown"),
                    page_number=payload.get("page_number"),
                    chunk_excerpt=payload.get("content", "")[:500],
                    relevance_score=round(result.score, 4),
                    sensitivity_tier=SensitivityTier(
                        payload.get("sensitivity_tier", "public")
                    ),
                    chunk_id=str(result.id),
                )
            )

        # 6. Build extractive answer from top chunks
        answer = self._build_extractive_answer(request.query, citations)

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "query_completed",
            user_id=user_id,
            collection=request.collection_name,
            retrieved=len(citations),
            redacted=chunks_redacted,
            duration_ms=round(elapsed_ms, 2),
        )

        return QueryResponse(
            answer=answer,
            citations=citations,
            chunks_retrieved=len(citations),
            chunks_redacted=chunks_redacted,
            query_time_ms=round(elapsed_ms, 2),
        )

    def _build_extractive_answer(self, query: str, citations: list[Citation]) -> str:
        """Build an extractive answer from the top citations."""
        if not citations:
            return "No relevant documents found for your query."

        parts = [f"Based on {len(citations)} relevant document(s):\n"]
        for i, c in enumerate(citations[:3], 1):
            source = f"[{c.document_name}"
            if c.page_number:
                source += f", p.{c.page_number}"
            source += f"] (score: {c.relevance_score})"
            parts.append(f"{i}. {source}\n   {c.chunk_excerpt[:300]}...")

        return "\n\n".join(parts)

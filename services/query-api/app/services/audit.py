from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import SensitivityTier
from app.models.query import QueryRequest, QueryResponse

logger = structlog.get_logger()


class AuditService:
    """Immutable audit logging for all query operations."""

    @staticmethod
    async def log_query(
        db: AsyncSession,
        user_id: str,
        request: QueryRequest,
        response: QueryResponse,
        user_clearance: SensitivityTier,
    ) -> None:
        """Log a query and its results to the audit trail."""
        chunk_ids_returned = [c.chunk_id for c in response.citations]
        # Summary is the first 500 chars of the answer
        summary = response.answer[:500] if response.answer else None

        await db.execute(
            text("""
                INSERT INTO audit_log (
                    user_id, query_text, collection_name, user_clearance,
                    chunks_retrieved, chunks_redacted,
                    chunk_ids_returned, chunk_ids_redacted,
                    response_summary, query_duration_ms
                ) VALUES (
                    :user_id, :query_text, :collection_name, :user_clearance,
                    :chunks_retrieved, :chunks_redacted,
                    :chunk_ids_returned, :chunk_ids_redacted,
                    :response_summary, :query_duration_ms
                )
            """),
            {
                "user_id": user_id,
                "query_text": request.query,
                "collection_name": request.collection_name,
                "user_clearance": user_clearance.value,
                "chunks_retrieved": response.chunks_retrieved,
                "chunks_redacted": response.chunks_redacted,
                "chunk_ids_returned": chunk_ids_returned,
                "chunk_ids_redacted": [],  # TODO: track specific redacted IDs
                "response_summary": summary,
                "query_duration_ms": response.query_time_ms,
            },
        )
        await db.commit()

        logger.info(
            "audit_logged",
            user_id=user_id,
            query_length=len(request.query),
            retrieved=response.chunks_retrieved,
            redacted=response.chunks_redacted,
        )

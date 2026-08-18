"""MCP tool handler implementations.

Each handler receives arguments from an MCP tool call and returns a dict result.
These operate with PUBLIC clearance by default for MCP clients (configurable).
"""

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.services.embedding import EmbeddingService

logger = structlog.get_logger()

# MCP tools use their own lightweight DB/Qdrant connections
_engine = create_async_engine(settings.postgres_dsn, pool_size=2)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

MCP_DEFAULT_CLEARANCE = "public"  # MCP clients get public access by default


def _get_qdrant() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def handle_search_documents(args: dict) -> dict:
    """Search documents using natural language query."""
    query = args["query"]
    collection = args.get("collection", "default")
    top_k = min(args.get("top_k", 5), 20)

    embedder = EmbeddingService.get_instance()
    query_vector = embedder.embed_query(query)

    # Apply public-only access filter for MCP clients
    access_filter = Filter(
        must=[
            FieldCondition(
                key="sensitivity_tier",
                match=MatchAny(any=[MCP_DEFAULT_CLEARANCE]),
            )
        ]
    )

    client = _get_qdrant()
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        query_filter=access_filter,
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for r in results:
        payload = r.payload or {}
        hits.append({
            "chunk_id": str(r.id),
            "source_file": payload.get("source_file", "unknown"),
            "page_number": payload.get("page_number"),
            "excerpt": payload.get("content", "")[:400],
            "relevance_score": round(r.score, 4),
            "sensitivity_tier": payload.get("sensitivity_tier", "public"),
        })

    return {"query": query, "collection": collection, "results": hits, "count": len(hits)}


async def handle_get_document_source(args: dict) -> dict:
    """Retrieve the full text of a specific chunk."""
    chunk_id = args["chunk_id"]
    client = _get_qdrant()

    # Retrieve chunk by ID from all collections
    try:
        # Search across known collections
        async with _session_factory() as db:
            result = await db.execute(text("SELECT name FROM collections"))
            collections = [row[0] for row in result.fetchall()]

        for col_name in collections:
            try:
                points = client.retrieve(collection_name=col_name, ids=[chunk_id], with_payload=True)
                if points:
                    payload = points[0].payload or {}
                    return {
                        "chunk_id": chunk_id,
                        "content": payload.get("content", ""),
                        "source_file": payload.get("source_file", "unknown"),
                        "page_number": payload.get("page_number"),
                        "document_id": payload.get("document_id"),
                        "sensitivity_tier": payload.get("sensitivity_tier"),
                    }
            except Exception:
                continue

        return {"error": f"Chunk {chunk_id} not found"}
    except Exception as e:
        return {"error": str(e)}


async def handle_list_collections(args: dict) -> dict:
    """List all collections with stats."""
    async with _session_factory() as db:
        result = await db.execute(
            text("""
                SELECT c.name, c.description, COUNT(d.id) as doc_count,
                       COALESCE(SUM(d.chunk_count), 0) as chunk_count
                FROM collections c
                LEFT JOIN documents d ON d.collection_id = c.id
                GROUP BY c.name, c.description
                ORDER BY c.name
            """)
        )
        rows = result.fetchall()

    collections = [
        {
            "name": row[0],
            "description": row[1],
            "document_count": row[2],
            "chunk_count": row[3],
        }
        for row in rows
    ]

    return {"collections": collections, "total": len(collections)}


async def handle_get_ingestion_status(args: dict) -> dict:
    """Get ingestion pipeline status."""
    async with _session_factory() as db:
        result = await db.execute(
            text("""
                SELECT status, COUNT(*) as count
                FROM ingestion_jobs
                GROUP BY status
            """)
        )
        rows = result.fetchall()

    return {"jobs_by_status": {row[0]: row[1] for row in rows}}


async def handle_summarize_document(args: dict) -> dict:
    """Generate an extractive summary from a document's chunks."""
    document_id = args["document_id"]
    max_chunks = min(args.get("max_chunks", 10), 20)

    client = _get_qdrant()

    # Find which collection has this document
    async with _session_factory() as db:
        result = await db.execute(
            text("""
                SELECT d.filename, c.name
                FROM documents d JOIN collections c ON c.id = d.collection_id
                WHERE d.id = :doc_id
            """),
            {"doc_id": document_id},
        )
        row = result.fetchone()

    if not row:
        return {"error": f"Document {document_id} not found"}

    filename, collection_name = row[0], row[1]

    # Get all chunks for this document, ordered by chunk_index
    doc_filter = Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        ]
    )

    results = client.scroll(
        collection_name=collection_name,
        scroll_filter=doc_filter,
        limit=max_chunks,
        with_payload=True,
    )

    chunks = sorted(
        results[0],
        key=lambda p: p.payload.get("chunk_index", 0) if p.payload else 0,
    )

    summary_parts = []
    for point in chunks:
        payload = point.payload or {}
        content = payload.get("content", "")
        page = payload.get("page_number")
        prefix = f"[Page {page}] " if page else ""
        summary_parts.append(f"{prefix}{content}")

    return {
        "document_id": document_id,
        "filename": filename,
        "collection": collection_name,
        "chunks_included": len(chunks),
        "summary": "\n\n---\n\n".join(summary_parts),
    }

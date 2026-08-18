from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.document import DocumentOut

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    collection_name: str = Query(default="default"),
    sensitivity_tier: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    """List documents with optional filters."""
    query = """
        SELECT d.id, d.filename, d.file_type, d.checksum, c.name AS collection_name,
               d.sensitivity_tier, d.chunk_count, d.file_size, d.ingested_at
        FROM documents d
        JOIN collections c ON c.id = d.collection_id
        WHERE c.name = :collection_name
    """
    params: dict = {"collection_name": collection_name, "limit": limit, "offset": offset}

    if sensitivity_tier:
        query += " AND d.sensitivity_tier = :sensitivity_tier"
        params["sensitivity_tier"] = sensitivity_tier

    query += " ORDER BY d.ingested_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        DocumentOut(
            id=row[0],
            filename=row[1],
            file_type=row[2],
            checksum=row[3],
            collection_name=row[4],
            sensitivity_tier=row[5],
            chunk_count=row[6],
            file_size=row[7],
            ingested_at=row[8],
        )
        for row in rows
    ]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Get metadata for a specific document."""
    result = await db.execute(
        text("""
            SELECT d.id, d.filename, d.file_type, d.checksum, c.name AS collection_name,
                   d.sensitivity_tier, d.chunk_count, d.file_size, d.ingested_at
            FROM documents d
            JOIN collections c ON c.id = d.collection_id
            WHERE d.id = :doc_id
        """),
        {"doc_id": str(doc_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentOut(
        id=row[0],
        filename=row[1],
        file_type=row[2],
        checksum=row[3],
        collection_name=row[4],
        sensitivity_tier=row[5],
        chunk_count=row[6],
        file_size=row[7],
        ingested_at=row[8],
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document and its chunks from PostgreSQL.

    Note: Qdrant vectors must be cleaned up separately via admin CLI.
    """
    result = await db.execute(
        text("DELETE FROM documents WHERE id = :doc_id RETURNING id"),
        {"doc_id": str(doc_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.commit()

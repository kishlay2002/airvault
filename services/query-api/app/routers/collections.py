from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.document import CollectionOut, CollectionCreate

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


@router.get("", response_model=list[CollectionOut])
async def list_collections(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CollectionOut]:
    """List all document collections."""
    result = await db.execute(
        text("""
            SELECT c.id, c.name, c.description, c.created_at,
                   COUNT(d.id) AS document_count
            FROM collections c
            LEFT JOIN documents d ON d.collection_id = c.id
            GROUP BY c.id, c.name, c.description, c.created_at
            ORDER BY c.created_at DESC
        """)
    )
    rows = result.fetchall()
    return [
        CollectionOut(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            document_count=row[4],
        )
        for row in rows
    ]


@router.post("", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionOut:
    """Create a new document collection."""
    # Check if name already exists
    existing = await db.execute(
        text("SELECT id FROM collections WHERE name = :name"),
        {"name": body.name},
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Collection '{body.name}' already exists",
        )

    result = await db.execute(
        text("""
            INSERT INTO collections (name, description)
            VALUES (:name, :description)
            RETURNING id, name, description, created_at
        """),
        {"name": body.name, "description": body.description},
    )
    await db.commit()
    row = result.fetchone()

    return CollectionOut(
        id=row[0], name=row[1], description=row[2], created_at=row[3], document_count=0
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a collection and all its documents."""
    if name == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default collection",
        )

    result = await db.execute(
        text("DELETE FROM collections WHERE name = :name RETURNING id"),
        {"name": name},
    )
    if not result.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    await db.commit()


@router.get("/{name}/stats")
async def collection_stats(
    name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get statistics for a collection."""
    result = await db.execute(
        text("""
            SELECT c.id, c.name, c.description, c.created_at,
                   COUNT(d.id) AS document_count,
                   COALESCE(SUM(d.chunk_count), 0) AS total_chunks,
                   COALESCE(SUM(d.file_size), 0) AS total_size_bytes
            FROM collections c
            LEFT JOIN documents d ON d.collection_id = c.id
            WHERE c.name = :name
            GROUP BY c.id, c.name, c.description, c.created_at
        """),
        {"name": name},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    return {
        "id": str(row[0]),
        "name": row[1],
        "description": row[2],
        "created_at": row[3].isoformat(),
        "document_count": row[4],
        "total_chunks": row[5],
        "total_size_bytes": row[6],
    }

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.audit import AuditEntryOut

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_entries(
    username: str | None = Query(default=None),
    collection_name: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO 8601 datetime"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AuditEntryOut]:
    """Query audit log entries with optional filters."""
    query = """
        SELECT a.id, a.user_id, u.username, a.query_text, a.collection_name,
               a.user_clearance, a.chunks_retrieved, a.chunks_redacted,
               a.response_summary, a.query_duration_ms, a.created_at
        FROM audit_log a
        JOIN users u ON u.id = a.user_id
        WHERE 1=1
    """
    params: dict = {"limit": limit, "offset": offset}

    if username:
        query += " AND u.username = :username"
        params["username"] = username

    if collection_name:
        query += " AND a.collection_name = :collection_name"
        params["collection_name"] = collection_name

    if since:
        query += " AND a.created_at >= :since"
        params["since"] = since

    query += " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        AuditEntryOut(
            id=row[0],
            user_id=row[1],
            username=row[2],
            query_text=row[3],
            collection_name=row[4],
            user_clearance=row[5],
            chunks_retrieved=row[6],
            chunks_redacted=row[7],
            response_summary=row[8],
            query_duration_ms=row[9],
            created_at=row[10],
        )
        for row in rows
    ]

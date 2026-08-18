import hashlib
import os
import tempfile
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])
logger = structlog.get_logger()

FILE_TYPE_MAP = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".wav": "audio",
    ".mp3": "audio",
    ".flac": "audio",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tiff": "image",
    ".tif": "image",
}


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Form(default="default"),
    user: dict = Depends(get_current_user),
) -> dict:
    """Upload a file for ingestion. Returns a job ID for tracking."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = os.path.splitext(file.filename)[1].lower()
    file_type = FILE_TYPE_MAP.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {list(FILE_TYPE_MAP.keys())}",
        )

    # Save to temp location
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()

    temp_dir = "/data/inbox"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{checksum}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    # Enqueue job via Redis
    job_id = str(uuid4())
    redis = Redis.from_url(settings.redis_url)

    try:
        await redis.rpush(
            "arq:queue",
            # arq expects specific job format, so we publish to a simple queue
            # that the worker picks up
            f"{job_id}|{file_path}|{file_type}|{checksum}|{len(content)}|{collection_name}",
        )
    finally:
        await redis.aclose()

    logger.info(
        "file_upload_accepted",
        job_id=job_id,
        filename=file.filename,
        file_type=file_type,
        size=len(content),
        collection=collection_name,
    )

    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_type": file_type,
        "checksum": checksum,
        "size_bytes": len(content),
        "collection": collection_name,
        "status": "queued",
    }


@router.get("/status")
async def ingestion_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get overall ingestion pipeline status."""
    result = await db.execute(
        text("""
            SELECT status, COUNT(*) as count
            FROM ingestion_jobs
            GROUP BY status
        """)
    )
    rows = result.fetchall()
    status_counts = {row[0]: row[1] for row in rows}

    # Redis queue depth
    try:
        redis = Redis.from_url(settings.redis_url)
        queue_depth = await redis.llen("arq:queue")
        await redis.aclose()
    except Exception:
        queue_depth = -1

    return {
        "queue_depth": queue_depth,
        "jobs": status_counts,
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get status of a specific ingestion job."""
    result = await db.execute(
        text("""
            SELECT id, file_path, file_type, status, retry_count,
                   error_message, created_at, updated_at
            FROM ingestion_jobs
            WHERE id = :job_id
        """),
        {"job_id": job_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": str(row[0]),
        "file_path": row[1],
        "file_type": row[2],
        "status": row[3],
        "retry_count": row[4],
        "error_message": row[5],
        "created_at": row[6].isoformat(),
        "updated_at": row[7].isoformat(),
    }

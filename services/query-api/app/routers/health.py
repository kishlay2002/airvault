import structlog
from fastapi import APIRouter
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health")
async def liveness() -> dict:
    """Liveness probe — API is running."""
    return {"status": "ok", "service": "vaultmind-query-api"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Readiness probe — all dependencies are reachable."""
    checks: dict = {}

    # PostgreSQL
    try:
        engine = create_async_engine(settings.postgres_dsn)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
        await engine.dispose()
    except Exception as e:
        checks["postgres"] = f"error: {str(e)}"

    # Redis
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        checks["redis"] = "ok"
        await redis.aclose()
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # Qdrant
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=5)
        client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = "ok" if all_ok else "degraded"

    return {"status": status_code, "checks": checks}

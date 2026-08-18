from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.services.auth import AuthService, api_key_header
from app.services.retrieval import RetrievalService
from app.services.embedding import EmbeddingService

# --- Database ---
_engine = create_async_engine(settings.postgres_dsn, pool_size=5, max_overflow=10)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


# --- Auth dependency ---
async def get_current_user(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in Authorization header",
        )
    return await AuthService.resolve_user(api_key, db)


# --- Services ---
_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service

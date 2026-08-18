from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_retrieval_service
from app.models.query import QueryRequest, QueryResponse
from app.services.audit import AuditService
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    retrieval: RetrievalService = Depends(get_retrieval_service),
) -> QueryResponse:
    """Submit a natural language query against the document knowledge base.

    Results are filtered by the caller's clearance level — chunks above
    the user's clearance are never returned.
    """
    response = await retrieval.query(
        request=request,
        user_clearance=user["clearance"],
        user_id=user["id"],
    )

    # Log audit trail
    await AuditService.log_query(
        db=db,
        user_id=user["id"],
        request=request,
        response=response,
        user_clearance=user["clearance"],
    )

    return response

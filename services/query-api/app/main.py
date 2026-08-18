"""VaultMind Query API

FastAPI application serving document intelligence queries with
compliance-aware retrieval and full audit trail.
"""

import asyncio
import sys

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.config import settings
from app.routers import query, collections, documents, users, audit, health, ingest
from app.services.embedding import EmbeddingService

# --- Structured Logging ---
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.log_level.upper(), structlog.INFO)
    ),
)

logger = structlog.get_logger()

# --- FastAPI App ---
app = FastAPI(
    title="VaultMind",
    description="Air-Gapped Document Intelligence Engine — Query API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Register routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(ingest.router)


@app.on_event("startup")
async def startup_event():
    """Pre-load embedding model on startup."""
    logger.info("api_starting", host=settings.host, port=settings.port)
    EmbeddingService.get_instance()
    logger.info("api_ready")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("api_shutting_down")


def main():
    """Entry point — run as REST API or MCP server based on CLI args."""
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        from app.mcp.server import run_mcp_stdio
        logger.info("starting_in_mcp_mode")
        asyncio.run(run_mcp_stdio())
    else:
        logger.info("starting_in_rest_mode")
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )


if __name__ == "__main__":
    main()

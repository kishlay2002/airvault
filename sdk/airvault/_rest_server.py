"""Thin REST API server wrapping the AirVault SDK.

This is NOT the core of AirVault — it's a convenience wrapper.
The real logic lives in airvault.engine.AirVault.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from uuid import UUID

from fastapi import FastAPI, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.security import APIKeyHeader

from airvault import AirVault, AirVaultConfig
from airvault.types import SensitivityTier

app = FastAPI(
    title="AirVault",
    description="Air-Gapped Document Intelligence SDK — REST API",
    version="0.1.0",
)

# Shared engine instance
_engine: AirVault | None = None


def get_engine() -> AirVault:
    global _engine
    if _engine is None:
        _engine = AirVault(AirVaultConfig())
    return _engine


# ── Health ─────────────────────────────────────────────────


@app.get("/health")
async def liveness():
    return {"status": "ok", "service": "airvault"}


@app.get("/health/ready")
async def readiness(engine: AirVault = Depends(get_engine)):
    health = await engine.health()
    return health.model_dump()


# ── Query ──────────────────────────────────────────────────


@app.post("/api/v1/query")
async def query_documents(
    body: dict,
    engine: AirVault = Depends(get_engine),
):
    result = await engine.query(
        text=body["query"],
        collection=body.get("collection", "default"),
        clearance=body.get("clearance", "public"),
        top_k=body.get("top_k", 5),
        user_id=body.get("user_id"),
    )
    return result.model_dump()


# ── Ingest ─────────────────────────────────────────────────


@app.post("/api/v1/ingest/upload", status_code=202)
async def upload_file(
    file: UploadFile = File(...),
    collection: str = Form(default="default"),
    sensitivity: str | None = Form(default=None),
    engine: AirVault = Depends(get_engine),
):
    content = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}")
    tmp.write(content)
    tmp.close()

    try:
        result = await engine.ingest(
            tmp.name,
            collection=collection,
            sensitivity=sensitivity,
        )
        return result.model_dump()
    finally:
        os.unlink(tmp.name)


# ── Collections ────────────────────────────────────────────


@app.get("/api/v1/collections")
async def list_collections(engine: AirVault = Depends(get_engine)):
    cols = await engine.list_collections()
    return [c.model_dump() for c in cols]


@app.post("/api/v1/collections", status_code=201)
async def create_collection(body: dict, engine: AirVault = Depends(get_engine)):
    col = await engine.create_collection(body["name"], body.get("description"))
    return col.model_dump()


@app.delete("/api/v1/collections/{name}", status_code=204)
async def delete_collection(name: str, engine: AirVault = Depends(get_engine)):
    await engine.delete_collection(name)


@app.get("/api/v1/collections/{name}/stats")
async def collection_stats(name: str, engine: AirVault = Depends(get_engine)):
    stats = await engine.collection_stats(name)
    return stats.model_dump()


# ── Documents ──────────────────────────────────────────────


@app.get("/api/v1/documents")
async def list_documents(
    collection: str = Query(default="default"),
    sensitivity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    engine: AirVault = Depends(get_engine),
):
    docs = await engine.list_documents(collection, sensitivity, limit)
    return [d.model_dump() for d in docs]


@app.get("/api/v1/documents/{doc_id}")
async def get_document(doc_id: UUID, engine: AirVault = Depends(get_engine)):
    doc = await engine.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump()


@app.delete("/api/v1/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, engine: AirVault = Depends(get_engine)):
    await engine.delete_document(doc_id)


# ── Audit ──────────────────────────────────────────────────


@app.get("/api/v1/audit")
async def query_audit(
    username: str | None = Query(default=None),
    since: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    engine: AirVault = Depends(get_engine),
):
    entries = await engine.audit_log(username, since, limit)
    return [e.model_dump() for e in entries]


@app.on_event("shutdown")
async def shutdown():
    if _engine:
        await _engine.close()

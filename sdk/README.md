# AirVault

**Air-Gapped Document Intelligence SDK**

A Python SDK that turns unstructured enterprise data into a queryable, access-controlled vector knowledge base — fully offline, zero external API calls, embeddable in any application.

```python
from airvault import AirVault

engine = AirVault()
await engine.ingest("contracts/nda.pdf", collection="legal")
results = await engine.query("What is the non-compete clause?", clearance="confidential")
print(results.citations[0].excerpt)
# → "The Employee shall not engage in competing business for 12 months..."
print(f"Redacted: {results.chunks_redacted} chunks above your clearance")
```

## Why AirVault?

- **Embeddable SDK** — `pip install airvault` → 5 lines to ingest + query. No server required.
- **Fully offline** — local embedding models, zero external API calls, air-gap deployable
- **Compliance-aware retrieval** — document sensitivity classification + user clearance enforced at the vector DB query level (not post-retrieval)
- **Multi-format** — PDFs, audio (Whisper), scanned images (OCR), text, Markdown
- **Audit trail** — every query, every chunk returned, every chunk redacted — logged
- **Multiple integration modes** — Python SDK, REST API, MCP server, File Drop

## Install

```bash
pip install airvault                  # Core SDK
pip install airvault[server]          # + REST API server
pip install airvault[mcp]             # + MCP server for AI agents
pip install airvault[all]             # Everything
```

## Try It Yourself (2 minutes)

### From PyPI (no repo needed)

```bash
# 1. Install
pip install airvault

# 2. Start Qdrant + PostgreSQL (Docker required)
docker run -d --name airvault-qdrant -p 6333:6333 qdrant/qdrant:latest
docker run -d --name airvault-postgres -p 5432:5432 \
  -e POSTGRES_USER=airvault -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=airvault postgres:16-alpine

# 3. Run the demo below (copy-paste into demo.py)
python demo.py
```

```python
# demo.py — full end-to-end in 30 lines
import asyncio
from airvault import AirVault, SensitivityTier

async def main():
    async with AirVault() as engine:
        # Ingest public and confidential documents
        await engine.ingest_text(
            "Quarterly revenue was $12.3M, up 15%. Customer retention at 94%.",
            source_name="earnings.txt", collection="demo",
            sensitivity=SensitivityTier.PUBLIC,
        )
        await engine.ingest_text(
            "CONFIDENTIAL: Merger with Nexus Corp at $200M. Board vote in Q3.",
            source_name="merger.txt", collection="demo",
            sensitivity=SensitivityTier.CONFIDENTIAL,
        )

        # PUBLIC user: cannot see merger details
        public = await engine.query("revenue and merger", collection="demo",
                                     clearance=SensitivityTier.PUBLIC)
        print(f"PUBLIC  → {public.chunks_retrieved} chunks, {public.chunks_redacted} redacted")

        # CONFIDENTIAL user: sees everything
        conf = await engine.query("revenue and merger", collection="demo",
                                   clearance=SensitivityTier.CONFIDENTIAL)
        print(f"CONFID  → {conf.chunks_retrieved} chunks, {conf.chunks_redacted} redacted")

        for c in conf.citations:
            print(f"  [{c.sensitivity.value}] {c.excerpt[:80]}...")

asyncio.run(main())
```

### From Source (for developers)

```bash
git clone https://github.com/kishlay2002/airvault.git && cd airvault
pip install -e "sdk/[dev]"
docker compose -f docker-compose.demo.yml up -d
cd sdk && pytest tests/ -v   # 62 tests, ~8 seconds
python examples/run_demo.py  # full E2E demo
```

The DB schema is **auto-created** on first use — no manual SQL needed.

## Quick Start

### As a Python SDK (in-process, no server)

```python
from airvault import AirVault, SensitivityTier

async with AirVault() as engine:
    # Ingest
    await engine.ingest("report.pdf", collection="hr")
    await engine.ingest_text("Confidential merger details...", collection="deals",
                             sensitivity=SensitivityTier.CONFIDENTIAL)

    # Query with access control
    results = await engine.query("merger timeline", collection="deals",
                                 clearance=SensitivityTier.INTERNAL)
    # → chunks_redacted=1 (CONFIDENTIAL chunk filtered for INTERNAL user)

# Sync wrapper for non-async code
from airvault import AirVaultSync
engine = AirVaultSync()
engine.ingest("report.pdf")
results = engine.query("quarterly revenue", clearance="internal")
```

### Configuration via Environment

```bash
export AIRVAULT_QDRANT_HOST=10.0.0.5
export AIRVAULT_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
export AIRVAULT_EMBEDDING_DIMENSION=768
export AIRVAULT_LOG_LEVEL=DEBUG

python my_app.py   # Config auto-loaded from env
```

### As a REST API

```bash
airvault serve --port 8000

curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "data retention policy", "clearance": "internal", "top_k": 5}'
```

### As an MCP Server (for AI agents)

```bash
airvault serve --mode mcp   # stdio transport
```

```json
// claude_desktop_config.json
{"mcpServers": {"airvault": {"command": "airvault", "args": ["serve", "--mode", "mcp"]}}}
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                Your Application                       │
│  from airvault import AirVault                      │
│  engine = AirVault(config)                           │
│  results = await engine.query(...)                    │
└──────────────────┬───────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │   AirVault SDK     │   ← The engine
         │  Extractors         │
         │  Chunker            │
         │  Embedder           │
         │  Classifier         │
         │  Access Filter      │   ← Core differentiator
         │  Audit Logger       │
         └────────┬────────────┘
                  │
    ┌─────────────▼──────────────┐
    │  Qdrant    │  PostgreSQL    │   ← Your infra (local)
    │  (vectors) │  (metadata)    │
    └────────────────────────────┘

  Optional wrappers (same SDK underneath):
  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
  │ REST API │ │MCP Server│ │Admin CLI│ │File Drop │
  │ (FastAPI)│ │ (stdio)  │ │ (Click) │ │(Go)      │
  └──────────┘ └──────────┘ └─────────┘ └──────────┘
```

## Compliance-Aware Retrieval (Key Differentiator)

Standard RAG retrieves chunks by similarity regardless of who is asking. AirVault filters at the Qdrant query level — restricted chunks are **never loaded into memory** for unauthorized users.

```python
# PUBLIC user queries "nuclear"
results = await engine.query("nuclear", clearance="public")
# → Only PUBLIC chunks returned
# → RESTRICTED "launch code" chunks are NEVER loaded
# → results.chunks_redacted = 1

# RESTRICTED user queries "nuclear"
results = await engine.query("nuclear", clearance="restricted")
# → All chunks returned (PUBLIC + RESTRICTED)
# → results.chunks_redacted = 0
```

See [examples/access_control_demo.py](examples/access_control_demo.py) for a full demo.

## SDK API

```python
async with AirVault(config) as engine:
    # Ingestion
    await engine.ingest(file_path, collection, sensitivity, metadata)
    await engine.ingest_batch(file_paths, collection)
    await engine.ingest_text(text, source_name, collection)

    # Querying
    result = await engine.query(text, collection, clearance, top_k)
    # → result.answer, result.citations, result.chunks_redacted

    # Collections
    await engine.list_collections()
    await engine.create_collection(name, description)
    await engine.collection_stats(name)

    # Documents
    await engine.list_documents(collection, sensitivity)
    await engine.get_document(doc_id)
    await engine.delete_document(doc_id)

    # Audit
    await engine.audit_log(username, since, limit)

    # Health
    await engine.health()  # {"status": "ok", "checks": {"postgres": "ok", ...}}

# Errors
from airvault import DuplicateDocumentError, UnsupportedFileTypeError, AirVaultError
try:
    await engine.ingest("report.pdf")
except DuplicateDocumentError:
    pass  # Already ingested (dedup by SHA-256)
except AirVaultError:  # Catch-all for any SDK error
    pass
```

## Project Structure

```
airvault/
├── engine.py             # AirVault class (main entry point)
├── config.py             # AirVaultConfig (pydantic-settings, env vars)
├── types.py              # SensitivityTier, QueryResult, Citation, IngestResult
├── errors.py             # AirVaultError hierarchy (typed exceptions)
├── sync.py               # AirVaultSync (sync wrapper for non-async code)
├── py.typed              # PEP 561 typing marker
├── ingestion/            # Extract → chunk → classify → embed → store
│   ├── pipeline.py       # Orchestrates the full ingestion flow
│   ├── chunker.py        # Sliding-window text chunking
│   ├── classifier.py     # Sensitivity auto-classification
│   └── extractors/       # PDF, audio (Whisper), image (OCR), text
├── embedding/            # Local sentence-transformers (batched)
├── retrieval/            # Query engine + access filter
│   ├── engine.py         # Semantic search with clearance enforcement
│   └── access.py         # Qdrant-level access control filter
├── storage/              # Qdrant (vectors) + PostgreSQL (metadata, audit)
├── _rest_server.py       # Optional FastAPI wrapper
└── _mcp_server.py        # Optional MCP server for AI agents
```

## Air-Gapped Deployment

The SDK is fully offline. The only network calls are to Qdrant + PostgreSQL on your own network.

```bash
# Connected machine: build + package
make build && bash deploy/scripts/airgap-package.sh

# Air-gapped machine: load + deploy
bash deploy/scripts/airgap-deploy.sh
```

All model weights baked into Docker images. `imagePullPolicy: Never`. Zero downloads at runtime.

## Embedding Models

Default: `BAAI/bge-small-en-v1.5` (33MB, 384d) — optimized for CPU-only, air-gapped environments.

Swap to a better model with one config change:

```python
from airvault import AirVault, AirVaultConfig

# Better quality (recommended if you have the resources)
config = AirVaultConfig(
    embedding_model="BAAI/bge-base-en-v1.5",
    embedding_dimension=768,
)

# Best quality (needs more RAM/CPU)
config = AirVaultConfig(
    embedding_model="BAAI/bge-large-en-v1.5",
    embedding_dimension=1024,
)

engine = AirVault(config)
```

| Model | Size | Dimensions | Quality | CPU Speed | Best For |
|-------|------|-----------|---------|-----------|----------|
| `bge-small-en-v1.5` (default) | 33MB | 384 | Good | ~5ms | Air-gapped, constrained hardware |
| `bge-base-en-v1.5` | 110MB | 768 | Better | ~15ms | General production use |
| `bge-large-en-v1.5` | 335MB | 1024 | Best | ~50ms | Maximum accuracy, GPU available |
| `all-MiniLM-L6-v2` | 80MB | 384 | Good | ~8ms | Popular alternative |

Any [sentence-transformers](https://huggingface.co/models?library=sentence-transformers) model works — just set the name and dimension.

## Security

- **Access control at retrieval boundary** — not post-retrieval, not at the API
- **Redaction counting without data access** — uses Qdrant `count()` with inverted filter; restricted content is never loaded into memory, even for metrics
- **Idempotent ingestion** — SHA-256 dedup prevents double-ingestion (configurable)
- **API key auth** — bcrypt-hashed, never stored plaintext
- **Sensitivity auto-classification** — rule-based, auditable, explainable
- **Immutable audit log** — no DELETE on audit table
- **Custom error hierarchy** — `AirVaultError` base class for safe error handling
- See [THREAT_MODEL.md](docs/THREAT_MODEL.md)

## Testing

```bash
cd sdk && pip install -e ".[dev]"
pytest tests/ -v                 # 62 tests, ~8 seconds
```

Tests cover: types, access filters, redaction filters, chunker, classifier, config (env vars), error hierarchy.

## License

MIT

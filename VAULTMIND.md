# VaultMind — Air-Gapped Document Intelligence SDK

> A Python SDK that turns unstructured enterprise data into a queryable, access-controlled vector knowledge base — fully offline, zero external API calls, embeddable in any application.

```python
from vaultmind import VaultMind

engine = VaultMind()
await engine.ingest("contracts/nda_acme.pdf", collection="legal")
results = await engine.query("What is the non-compete clause?", clearance="confidential")
print(results.citations[0].excerpt)
```

---

## Table of Contents

1. [What VaultMind Is](#what-vaultmind-is)
2. [Problem Statement](#problem-statement)
3. [Who Uses This and Why](#who-uses-this-and-why)
4. [SDK API Design](#sdk-api-design)
5. [Architecture](#architecture)
6. [Core Modules](#core-modules)
7. [Compliance-Aware Retrieval (Differentiator)](#compliance-aware-retrieval)
8. [Integration Modes](#integration-modes)
9. [Data Models](#data-models)
10. [REST API Reference](#rest-api-reference)
11. [MCP Server Interface](#mcp-server-interface)
12. [Ingestion Pipeline](#ingestion-pipeline)
13. [Query Pipeline](#query-pipeline)
14. [Security Architecture](#security-architecture)
15. [Deployment](#deployment)
16. [Observability](#observability)
17. [Database Schema](#database-schema)
18. [Tech Stack](#tech-stack)
19. [Project Structure](#project-structure)
20. [Testing Strategy](#testing-strategy)
21. [Trade-offs & Design Decisions](#trade-offs--design-decisions)

---

## What VaultMind Is

VaultMind is a **Python SDK** (+ optional REST server + MCP server) that provides:

1. **Ingest** — Feed it PDFs, audio recordings, scanned images, text files → it extracts, chunks, embeds, classifies sensitivity, and stores vectors
2. **Query** — Ask natural language questions → it retrieves relevant chunks filtered by the caller's clearance level
3. **Audit** — Every query is logged with what was returned and what was redacted

It runs **entirely offline**. No OpenAI, no Pinecone, no cloud APIs. All models are local. Developers embed it in their own applications via `pip install vaultmind` or deploy the included REST/MCP server.

**VaultMind is NOT:**
- A chatbot or UI
- A wrapper around OpenAI
- A SaaS product

**VaultMind IS:**
- An embeddable engine (like SQLite is for relational data, VaultMind is for document intelligence)
- An SDK that developers integrate into their own apps
- A self-hosted REST API and MCP server for teams that prefer HTTP/agent integration

---

## Problem Statement

Enterprises in regulated industries (defense, healthcare, legal, finance) sit on massive volumes of unstructured data they need to search intelligently — but:

1. **Cloud AI is banned** — air-gapped networks, data sovereignty laws, HIPAA/SOC2/ISO 27001 prohibit sending data to external APIs
2. **Keyword search is broken** — Elasticsearch doesn't understand "What's the penalty for early termination?" when the document says "liquidated damages"
3. **No access control in RAG** — every open-source RAG demo retrieves the most relevant chunks regardless of who is asking. A junior intern sees the same classified chunks as the CISO
4. **Integration is hard** — most AI tools are standalone apps, not libraries. Developers can't embed them into existing enterprise software

VaultMind solves all four by providing a **pip-installable engine** with built-in access control, offline embedding, and multi-format ingestion.

---

## Who Uses This and Why

| User | Problem | How VaultMind Helps |
|------|---------|-------------------|
| **Enterprise developer** building an internal knowledge portal | Needs semantic search over company docs without sending data to the cloud | `pip install vaultmind` → 5 lines of code to ingest + query |
| **Defense/IC contractor** building a classified document system | Air-gapped network, no internet, must enforce clearance levels | Fully offline engine with compliance-aware retrieval at the vector boundary |
| **Healthcare startup** building a clinical trial search tool | Patient data under HIPAA — cannot use OpenAI | Local embedding models, full audit trail, zero egress |
| **Legal tech company** building a contract analysis tool | Needs to search across 10,000 NDAs with sensitivity filtering | Multi-format ingestion (PDF + OCR) with per-document sensitivity classification |
| **AI agent developer** building a RAG agent with tool use | Needs document search as an MCP tool for Claude/Cursor integration | Built-in MCP server exposes `search_documents`, `summarize_document`, etc. |
| **DevOps engineer** deploying AI tooling on-prem | Needs single-command deployment, health checks, runbooks | Docker Compose / Helm chart, Prometheus metrics, structured logging |

---

## SDK API Design

### Installation

```bash
pip install vaultmind                    # Core SDK
pip install vaultmind[server]            # + REST API server
pip install vaultmind[mcp]               # + MCP server
pip install vaultmind[all]               # Everything
```

### Quick Start (5 lines)

```python
from vaultmind import VaultMind

engine = VaultMind()                                          # connects to local Qdrant + PostgreSQL
await engine.ingest("path/to/report.pdf", collection="hr")    # extract → chunk → embed → store
results = await engine.query("parental leave policy", clearance="internal")

for cite in results.citations:
    print(f"[{cite.source}:{cite.page}] {cite.excerpt}")
print(f"Redacted: {results.chunks_redacted} chunks above your clearance")
```

### Full API Surface

```python
from vaultmind import VaultMind, VaultMindConfig, SensitivityTier

# --- Configuration ---
config = VaultMindConfig(
    qdrant_url="localhost:6333",
    postgres_dsn="postgresql+asyncpg://user:pass@localhost:5432/vaultmind",
    embedding_model="BAAI/bge-small-en-v1.5",  # any sentence-transformers model
    chunk_size=512,
    chunk_overlap=64,
    log_level="INFO",
)
engine = VaultMind(config)

# --- Ingestion ---
job = await engine.ingest(
    "path/to/file.pdf",                # str or pathlib.Path
    collection="contracts",             # target collection (auto-created)
    sensitivity=SensitivityTier.CONFIDENTIAL,  # manual override (optional)
    metadata={"department": "legal"},   # custom metadata (optional)
)
print(job.id, job.status, job.chunk_count)

# Batch ingest
jobs = await engine.ingest_batch(
    ["doc1.pdf", "doc2.pdf", "report.wav"],
    collection="mixed",
)

# Ingest raw text
await engine.ingest_text(
    "This is a policy document about data retention...",
    source_name="retention_policy.txt",
    collection="policies",
)

# --- Querying ---
results = await engine.query(
    "What is the data retention period?",
    collection="policies",
    clearance=SensitivityTier.INTERNAL,  # user's clearance level
    top_k=5,
)
# results.answer           → extractive answer string
# results.citations         → list[Citation] with source, page, excerpt, score
# results.chunks_retrieved  → int
# results.chunks_redacted   → int (chunks above clearance, filtered at vector DB)
# results.query_time_ms     → float

# --- Collections ---
collections = await engine.list_collections()
stats = await engine.collection_stats("contracts")
await engine.create_collection("new-collection", description="...")
await engine.delete_collection("old-collection")

# --- Documents ---
docs = await engine.list_documents(collection="contracts", sensitivity="confidential")
doc = await engine.get_document(doc_id)
await engine.delete_document(doc_id)

# --- Audit ---
entries = await engine.audit_log(username="analyst-1", since="2025-01-01", limit=50)

# --- Health ---
health = await engine.health()  # {"status": "ok", "checks": {"postgres": "ok", ...}}

# --- Lifecycle ---
await engine.close()  # clean up connections
```

### Sync Wrapper (for non-async codebases)

```python
from vaultmind import VaultMindSync

engine = VaultMindSync()
engine.ingest("report.pdf")
results = engine.query("quarterly revenue", clearance="internal")
engine.close()
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Developer's Application                        │
│                                                                         │
│   from vaultmind import VaultMind                                       │
│   engine = VaultMind(config)                                            │
│   results = await engine.query(...)                                     │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
              ┌─────────────▼───────────────┐
              │       VaultMind SDK          │
              │                             │
              │  ┌────────┐  ┌───────────┐  │
              │  │Ingest  │  │  Query     │  │
              │  │Pipeline│  │  Engine    │  │
              │  └───┬────┘  └─────┬─────┘  │
              │      │             │         │
              │  ┌───▼─────────────▼─────┐  │
              │  │   Core Services       │  │
              │  │  ┌─────────────────┐  │  │
              │  │  │ Extractors      │  │  │
              │  │  │ Chunker         │  │  │
              │  │  │ Embedder        │  │  │
              │  │  │ Classifier      │  │  │
              │  │  │ Access Filter   │  │  │
              │  │  │ Audit Logger    │  │  │
              │  │  └─────────────────┘  │  │
              │  └───────────┬───────────┘  │
              └──────────────┼──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │       Storage Layer          │
              │  ┌────────┐ ┌──────────┐    │
              │  │ Qdrant │ │PostgreSQL│    │
              │  │(vectors│ │(metadata,│    │
              │  │+payload│ │ audit)   │    │
              │  └────────┘ └──────────┘    │
              └─────────────────────────────┘

   Optional wrappers (same SDK underneath):
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────┐
   │  REST API   │  │ MCP Server  │  │ Admin CLI    │  │File      │
   │  (FastAPI)  │  │ (stdio/SSE) │  │ (Click)      │  │Sentinel  │
   │             │  │             │  │              │  │(Go)      │
   └─────────────┘  └─────────────┘  └──────────────┘  └──────────┘
```

The SDK is the **engine**. The REST API, MCP server, CLI, and File Sentinel are all **thin wrappers** that call the same SDK methods. This means:
- You can embed VaultMind as a library in your Python app (no server needed)
- You can run it as a REST API for language-agnostic integration
- You can expose it as MCP tools for AI agents
- All three modes share the same ingestion pipeline, access control logic, and audit trail

### Air-Gap Model

```
Internet ─────────── FIREWALL ─────────── Your Network
                         │
     Nothing crosses     │     ┌──────────────────────────┐
     this boundary       │     │   Your Application       │
     at runtime          │     │   + VaultMind SDK         │
                         │     │   + Qdrant + PostgreSQL   │
                         │     │   + Embedding Model       │
                         │     │   (all local)             │
                         │     └──────────────────────────┘
```

The only network calls VaultMind makes are to Qdrant and PostgreSQL **on your own network**. Zero internet. The embedding model is loaded from local disk.

---

## Core Modules

### 1. Extractors (Text Extraction)

| File Type | Extractor | Library | Notes |
|-----------|-----------|---------|-------|
| PDF (text) | `PDFExtractor` | PyMuPDF (`fitz`) | Layout-aware, preserves tables |
| PDF (scanned) | `PDFExtractor` | PyMuPDF + pytesseract | OCR fallback if text < 50 chars/page |
| Audio (WAV/MP3/FLAC) | `AudioExtractor` | faster-whisper | Local Whisper model, no API |
| Images (PNG/JPG/TIFF) | `ImageExtractor` | pytesseract | Preprocessing: grayscale, threshold |
| Text / Markdown | `TextExtractor` | chardet | Encoding detection |

All extractors implement `BaseExtractor` ABC → plug in your own via `engine.register_extractor()`.

### 2. Chunker

Recursive character splitting with:
- Configurable chunk size (default 512 tokens) and overlap (default 64 tokens)
- Separator hierarchy: `\n\n` → `\n` → `. ` → ` `
- Page-aware chunking for PDFs (preserves page number in metadata)
- Minimum chunk size to skip tiny fragments

### 3. Embedder

- Singleton service using `sentence-transformers`
- Default: `BAAI/bge-small-en-v1.5` (33M params, 384-dim, CPU-friendly)
- Loaded once, shared across all operations
- Configurable: swap any `sentence-transformers` model via config

### 4. Sensitivity Classifier

Rule-based classification (auditable, explainable):
- **RESTRICTED** — "classified", "top secret", "eyes only"
- **CONFIDENTIAL** — "confidential", "proprietary", "trade secret"
- **INTERNAL** — "internal only", "do not distribute", "draft"
- **PUBLIC** — default (no keywords matched)

Manual override available at ingest time. Rules can be extended.

### 5. Access Filter

The core differentiator. See [Compliance-Aware Retrieval](#compliance-aware-retrieval).

### 6. Audit Logger

Every query logged to PostgreSQL with:
- User identity + clearance level
- Query text + collection
- Chunks returned (IDs + content summary)
- Chunks redacted (count + IDs)
- Query duration
- Timestamp

Immutable — no UPDATE or DELETE on audit table.

---

## Compliance-Aware Retrieval

This is VaultMind's **key differentiator** over every other RAG library.

### The Problem with Standard RAG

```
Standard RAG:
  User queries "nuclear" → retrieves top-5 chunks by similarity
  Chunk #1: "Nuclear launch code procedures" (RESTRICTED) ← LEAKED
  Chunk #2: "Nuclear energy basics" (PUBLIC)               ← OK
```

Every open-source RAG demo has this problem. LangChain, LlamaIndex, Haystack — none enforce access control at the retrieval boundary.

### How VaultMind Solves It

```
VaultMind:
  User queries "nuclear" with clearance=PUBLIC
  → Qdrant filter: sensitivity_tier IN ["public"]
  → Chunk #1 is NEVER LOADED into memory
  → Only PUBLIC chunks returned
  → Response includes: chunks_redacted=1
  → Audit log records: what was filtered and why
```

### Implementation

```python
from qdrant_client.models import Filter, FieldCondition, MatchAny

def build_access_filter(user_clearance: SensitivityTier) -> Filter:
    """Build Qdrant filter that only returns chunks at or below user's clearance."""
    tier_order = ["public", "internal", "confidential", "restricted"]
    allowed = []
    for tier in tier_order:
        allowed.append(tier)
        if tier == user_clearance.value:
            break

    return Filter(
        must=[
            FieldCondition(
                key="sensitivity_tier",
                match=MatchAny(any=allowed),
            )
        ]
    )
```

### Why Filter at the Vector DB, Not the API?

| Approach | Problem |
|----------|---------|
| Post-retrieval filtering (API layer) | Restricted chunks are loaded into memory, consume search capacity, and can leak via relevance scores or result counts |
| **Pre-retrieval filtering (Qdrant query)** | Restricted chunks are **never loaded into memory**. Zero information leakage. |

VaultMind filters at the Qdrant query level — defense-in-depth.

---

## Integration Modes

### Mode 1: Python SDK (In-Process)

```python
# Your application directly imports and uses VaultMind
from vaultmind import VaultMind

engine = VaultMind()
results = await engine.query("revenue forecast", clearance="internal")
```

**Best for:** Python applications that want zero network overhead. The engine runs in your process.

### Mode 2: REST API Server

```bash
# Start the server
vaultmind serve --host 0.0.0.0 --port 8000

# Call from any language
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <api-key>" \
  -d '{"query": "revenue forecast", "top_k": 5}'
```

**Best for:** Non-Python apps, microservice architectures, multi-client setups.

### Mode 3: MCP Server

```bash
# Start as MCP server (stdio transport for local agents)
vaultmind serve --mode mcp
```

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "vaultmind": {
      "command": "vaultmind",
      "args": ["serve", "--mode", "mcp"]
    }
  }
}
```

**Best for:** AI agent integration (Claude Desktop, Cursor, custom agents).

### Mode 4: File Drop (Go Sidecar)

```bash
# File Sentinel watches a directory and auto-ingests
cp document.pdf /data/inbox/
# → File Sentinel detects → enqueues → Ingestion Worker processes
```

**Best for:** Batch ingestion, legacy workflows, operators who don't write code.

---

## Data Models

```python
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


class SensitivityTier(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    def allowed_tiers(self) -> list[str]:
        order = [self.PUBLIC, self.INTERNAL, self.CONFIDENTIAL, self.RESTRICTED]
        return [t.value for t in order[:order.index(self) + 1]]


class FileType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"


# --- SDK Response Types ---

class Citation(BaseModel):
    source: str                        # filename
    page: int | None = None            # page number (PDFs)
    excerpt: str                       # chunk text (truncated)
    score: float                       # relevance score
    sensitivity: SensitivityTier
    chunk_id: str

class QueryResult(BaseModel):
    answer: str                        # extractive answer
    citations: list[Citation]
    chunks_retrieved: int
    chunks_redacted: int               # filtered by access control
    query_time_ms: float

class IngestResult(BaseModel):
    id: UUID
    filename: str
    file_type: FileType
    chunk_count: int
    sensitivity: SensitivityTier
    status: str                        # "completed" | "failed"

class CollectionInfo(BaseModel):
    name: str
    description: str | None
    document_count: int
    chunk_count: int
    created_at: datetime

class HealthStatus(BaseModel):
    status: str                        # "ok" | "degraded"
    checks: dict[str, str]            # {"postgres": "ok", "qdrant": "ok", ...}
```

---

## REST API Reference

The REST server is a thin FastAPI wrapper around the SDK.

### Ingestion
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ingest/upload` | Upload a file for ingestion |
| `GET` | `/api/v1/ingest/status` | Queue depth + job counts by status |
| `GET` | `/api/v1/ingest/jobs/{job_id}` | Status of a specific job |

### Query
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/query` | Submit a natural language query |

### Collections
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/collections` | List all collections |
| `POST` | `/api/v1/collections` | Create a new collection |
| `DELETE` | `/api/v1/collections/{name}` | Delete a collection |
| `GET` | `/api/v1/collections/{name}/stats` | Collection statistics |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/documents` | List documents (with filters) |
| `GET` | `/api/v1/documents/{id}` | Document metadata |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + chunks |

### Users & Auth
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/users` | List users |
| `POST` | `/api/v1/users` | Create user (returns API key once) |
| `PATCH` | `/api/v1/users/{id}` | Update clearance |
| `DELETE` | `/api/v1/users/{id}` | Deactivate user |

### Audit
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/audit` | Query audit log |

### Health
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness (all deps reachable) |
| `GET` | `/metrics` | Prometheus metrics |

---

## MCP Server Interface

VaultMind exposes 5 MCP tools for AI agent integration:

| Tool | Description |
|------|-------------|
| `search_documents` | Natural language search with collection + top_k params |
| `get_document_source` | Retrieve full chunk text by ID |
| `list_collections` | List all collections with stats |
| `get_ingestion_status` | Pipeline status: queue depth, job counts |
| `summarize_document` | Extractive summary from a document's chunks |

MCP clients connect via `stdio` (local) or `SSE` (networked).

---

## Ingestion Pipeline

```
File → Extract → Clean → Chunk → Classify → Embed → Store
                                      │           │
                                      │           ├──▶ Qdrant (vectors + payload)
                                      │           └──▶ PostgreSQL (metadata)
                                      │
                                      └──▶ Sensitivity tier assigned per-chunk
```

### Extraction by File Type

| File Type | Library | Notes |
|-----------|---------|-------|
| PDF (text) | PyMuPDF | Layout-aware, preserves tables |
| PDF (scanned) | PyMuPDF + pytesseract | OCR fallback if text < 50 chars/page |
| Audio | faster-whisper | Local Whisper, baked into image |
| Images | pytesseract | Grayscale + threshold preprocessing |
| Text/MD | chardet | Encoding detection |

### Chunking

- Recursive character split: `\n\n` → `\n` → `. ` → ` `
- Default: 512 tokens, 64 overlap, 50 minimum
- Page-aware for PDFs (chunk knows which page it came from)

### Embedding

- `BAAI/bge-small-en-v1.5` — 33M params, 384 dimensions, CPU-friendly
- Loaded once at startup, shared across all operations
- Normalized embeddings for cosine similarity

### Failure Handling

```
Fail → retry (30s) → retry (120s) → retry (480s) → dead-letter queue
```

---

## Query Pipeline

```python
async def query(text, collection, clearance, top_k):
    vector = embed(text)                        # 1. Embed query
    access_filter = build_filter(clearance)      # 2. Build clearance filter
    results = qdrant.search(vector, filter)      # 3. Search (pre-filtered)
    total = qdrant.search(vector, no_filter)     # 4. Count total (for redaction count)
    redacted = len(total) - len(results)         # 5. Compute redacted
    answer = extractive_answer(results)          # 6. Build answer from top chunks
    audit_log(user, text, results, redacted)     # 7. Log audit trail
    return QueryResult(answer, citations, redacted)
```

---

## Security Architecture

```
Layer 1: Network         → mTLS between services, zero external egress
Layer 2: Authentication  → API key per user, bcrypt-hashed, never stored plaintext
Layer 3: Authorization   → Clearance-based filtering at vector retrieval boundary
Layer 4: Data Integrity  → SHA-256 checksums on ingested files, signed model artifacts
Layer 5: Audit           → Immutable audit log, no DELETE on audit table
Layer 6: Container       → Non-root, read-only filesystem, no shell in prod images
```

---

## Deployment

### As a Python Library

```bash
pip install vaultmind
# Requires: running Qdrant + PostgreSQL (bring your own or use docker-compose)
```

### Docker Compose (Full Stack)

```bash
git clone https://github.com/kishlay2002/vaultmind.git
cd vaultmind && make dev
# Starts: Qdrant + PostgreSQL + Redis + API + Worker + File Sentinel
```

### Kubernetes (K3s + Helm)

```bash
helm install vaultmind deploy/helm/vaultmind
```

### Air-Gapped

```bash
# Connected machine: package everything
make build && bash deploy/scripts/airgap-package.sh

# Air-gapped machine: load + deploy
bash deploy/scripts/airgap-deploy.sh
```

All model weights baked into Docker images. `imagePullPolicy: Never`. Zero downloads at runtime.

---

## Observability

- **Structured logging** — JSON via `structlog` (Python), `zerolog` (Go)
- **Prometheus metrics** — `vaultmind_query_duration_seconds`, `vaultmind_ingestion_jobs_total`, `vaultmind_chunks_redacted`
- **Health checks** — `/health` (liveness), `/health/ready` (readiness: Qdrant + PG + Redis)
- **Runbook** — `docs/RUNBOOK.md` for operators
- **Threat model** — `docs/THREAT_MODEL.md` with asset list, threat matrix, trust boundaries

---

## Database Schema

### PostgreSQL

```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    checksum VARCHAR(64) NOT NULL UNIQUE,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    sensitivity_tier VARCHAR(20) NOT NULL DEFAULT 'public',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    file_size BIGINT NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    clearance VARCHAR(20) NOT NULL DEFAULT 'public',
    api_key_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    collection_name VARCHAR(255),
    user_clearance VARCHAR(20) NOT NULL,
    chunks_retrieved INTEGER NOT NULL,
    chunks_redacted INTEGER NOT NULL,
    response_summary TEXT,
    query_duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Qdrant Payload Schema (per vector point)

```json
{
    "document_id": "uuid",
    "chunk_index": 0,
    "content": "chunk text...",
    "page_number": 12,
    "sensitivity_tier": "internal",
    "source_file": "report.pdf",
    "collection_name": "policies"
}
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| SDK Core | Python 3.12, Pydantic v2 | Typed, async, widely adopted |
| REST Server | FastAPI | Async, auto-generated OpenAPI docs |
| MCP Server | MCP Python SDK | Official protocol for AI agent tools |
| Vector DB | Qdrant | Metadata filtering (critical for access control), self-hosted |
| Relational DB | PostgreSQL 16 | ACID, mature |
| Queue | Redis 7 + arq | Async-native job processing |
| Embeddings | sentence-transformers | Local CPU inference, swappable models |
| OCR | Tesseract | Open-source, offline |
| Audio | faster-whisper | Optimized Whisper, local inference |
| PDF | PyMuPDF | Fast, layout-aware |
| File Watcher | Go 1.22 + fsnotify | 5MB static binary, zero deps |
| CLI | Click + Rich | Beautiful terminal output |
| Containers | Docker (multi-stage) | Minimal images, air-gap ready |
| Orchestration | K3s + Helm | Lightweight Kubernetes for on-prem |
| Logging | structlog / zerolog | Structured JSON |
| Metrics | Prometheus | Industry standard |

---

## Project Structure

```
vaultmind/
├── sdk/                              # ← THE CORE: pip install vaultmind
│   ├── vaultmind/
│   │   ├── __init__.py               # Public API: VaultMind, VaultMindSync
│   │   ├── engine.py                 # VaultMind class (main entry point)
│   │   ├── config.py                 # VaultMindConfig
│   │   ├── types.py                  # SensitivityTier, QueryResult, Citation, etc.
│   │   ├── ingestion/
│   │   │   ├── pipeline.py           # Orchestrates extract → chunk → embed → store
│   │   │   ├── extractors/           # PDF, audio, image, text extractors
│   │   │   ├── chunker.py            # Recursive character splitter
│   │   │   └── classifier.py         # Sensitivity classification
│   │   ├── embedding/
│   │   │   └── service.py            # Singleton embedding model
│   │   ├── retrieval/
│   │   │   ├── engine.py             # Query execution + access filtering
│   │   │   └── access.py             # build_access_filter()
│   │   ├── storage/
│   │   │   ├── qdrant.py             # Qdrant client wrapper
│   │   │   └── postgres.py           # Async PostgreSQL operations
│   │   └── audit/
│   │       └── logger.py             # Audit trail logging
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
│
├── server/                           # REST API (thin FastAPI wrapper around SDK)
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/                  # query, collections, documents, users, audit, health, ingest
│   │   ├── dependencies.py           # Auth, DB session, SDK instance
│   │   └── mcp/                      # MCP server (calls SDK methods)
│   ├── Dockerfile
│   └── pyproject.toml
│
├── services/
│   ├── ingestion-worker/             # arq worker (calls SDK pipeline)
│   └── file-sentinel/                # Go file watcher
│
├── cli/                              # Admin CLI (calls SDK or REST API)
├── deploy/                           # Docker, Helm, air-gap scripts
├── migrations/                       # PostgreSQL schema
├── docs/                             # RUNBOOK, THREAT_MODEL
├── examples/                         # Usage examples
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## Testing Strategy

### Unit Tests
- **Chunker** — empty text, single char, exact boundary, overlap correctness
- **Classifier** — keyword detection, case insensitivity, tier ordering
- **Access filter** — every clearance level produces correct allowed tiers
- **Auth** — API key generation, hashing, verification

### Integration Tests
- **Full pipeline** — ingest PDF → verify chunks in Qdrant + metadata in PG
- **Access control** — ingest RESTRICTED + PUBLIC docs → query as PUBLIC → only PUBLIC returned
- **Redaction count** — verify `chunks_redacted` matches actual filtered count
- **Audit trail** — verify audit entry created for every query

### Key Test (the one that matters most)

```python
async def test_restricted_chunks_never_leak():
    engine = VaultMind(test_config)
    await engine.ingest("classified_nuclear.pdf", sensitivity="restricted")
    await engine.ingest("public_nuclear.pdf", sensitivity="public")

    results = await engine.query("nuclear", clearance="public")

    assert all(c.sensitivity == "public" for c in results.citations)
    assert results.chunks_redacted > 0
```

---

## Trade-offs & Design Decisions

| Decision | Chosen | Alternative | Why |
|----------|--------|-------------|-----|
| SDK-first vs. API-first | SDK-first | API-first | Developers embed it; API is just a wrapper |
| Embedding model | bge-small (384d) | bge-large (1024d) | CPU-friendly for constrained envs |
| Vector DB | Qdrant | Chroma, Weaviate | Best metadata filtering for access control |
| Job queue | arq (Redis) | Celery | Async-native, lightweight |
| Chunking | Recursive split | Semantic chunking | Deterministic, no model dependency |
| Answer gen | Extractive (default) | Generative (LLM) | No LLM dependency; LLM mode is opt-in |
| Classifier | Rule-based | ML classifier | Auditable, explainable — critical for compliance |
| Access filter | Qdrant pre-filter | Post-retrieval | Restricted chunks never loaded into memory |
| Go for sentinel | Yes | Python watchdog | 5MB binary, better fs events |

---

## Interview Talking Points

1. **"I designed it as an SDK, not an app."** — Shows you think about developer experience and composability, not just features.

2. **"Access control is at the vector retrieval boundary, not the API layer."** — Restricted chunks are never loaded into memory for unauthorized users. Prevents information leakage via relevance scores.

3. **"The classifier is rule-based because rules are auditable."** — You can explain to a compliance officer why a document was classified as CONFIDENTIAL. You can't explain a neural network's decision.

4. **"The REST API and MCP server are 50-line wrappers around the SDK."** — Everything is the same engine. Swap the integration mode without changing business logic.

5. **"Every deployment decision was for a field operator, not a developer."** — CLI, runbook, health checks, structured logging, air-gap packaging — operable without you in the room.
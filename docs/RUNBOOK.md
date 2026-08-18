# VaultMind Operations Runbook

This document is for deployment engineers operating VaultMind without developer support.

## Quick Reference

| Service | Port | Health Check |
|---------|------|-------------|
| Query API | 8000 | `curl http://localhost:8000/health` |
| PostgreSQL | 5432 | `pg_isready -U vaultmind` |
| Redis | 6379 | `redis-cli ping` |
| Qdrant | 6333 | `curl http://localhost:6333/healthz` |

## Common Issues

### 1. Query API returns 503

**Symptom:** `/health/ready` shows degraded status.

**Steps:**
1. Check which dependency is down: `curl http://localhost:8000/health/ready`
2. If PostgreSQL: `docker compose logs postgres` — check for disk space or connection limits
3. If Qdrant: `docker compose restart qdrant` — verify storage volume is mounted
4. If Redis: `docker compose restart redis`

### 2. Ingestion Jobs Stuck

**Symptom:** Files in inbox but not appearing in search.

**Steps:**
1. Check queue depth: `vaultmind ingest status`
2. Check worker logs: `docker compose logs ingestion-worker`
3. If worker crashed: `docker compose restart ingestion-worker`
4. Check dead-letter queue: `vaultmind ingest dead-letter list`

### 3. Queries Return Empty Results

**Steps:**
1. Verify collection exists: `vaultmind collections list`
2. Verify documents ingested: check collection stats
3. Check user clearance: query may be filtered by access control
4. Check Qdrant health: `curl http://localhost:6333/collections`

### 4. High Query Latency

**Steps:**
1. Check embedding model memory: `docker stats vaultmind-query-api`
2. Check Qdrant indexing: if recently ingested many docs, HNSW index may be rebuilding
3. Check Redis cache hit rate: `redis-cli INFO stats | grep keyspace`

### 5. Disk Space

**Cleanup commands:**
```bash
# Qdrant snapshots
docker compose exec qdrant rm -rf /qdrant/storage/snapshots/*

# PostgreSQL audit log rotation (keep last 90 days)
docker compose exec postgres psql -U vaultmind -c \
  "DELETE FROM audit_log WHERE created_at < now() - interval '90 days';"
```

## Startup Sequence

Services must start in this order:
1. PostgreSQL → Redis → Qdrant (data layer)
2. Ingestion Worker → Query API (application layer)
3. File Sentinel (file watcher)

Docker Compose handles this via `depends_on` with health checks.

## Shutdown

```bash
docker compose down        # graceful shutdown
docker compose down -v     # shutdown + delete all data volumes
```

## Log Locations

All services output structured JSON logs to stdout.

```bash
docker compose logs -f query-api          # query API logs
docker compose logs -f ingestion-worker   # ingestion logs
docker compose logs -f file-sentinel      # file watcher logs
```

## Backup

```bash
# PostgreSQL
docker compose exec postgres pg_dump -U vaultmind vaultmind > backup.sql

# Qdrant snapshots
curl -X POST http://localhost:6333/collections/default/snapshots
```

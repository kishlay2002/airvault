-- VaultMind: Initial Schema
-- V001

-- Collections
CREATE TABLE IF NOT EXISTS collections (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Seed default collection
INSERT INTO collections (name, description)
VALUES ('default', 'Default document collection')
ON CONFLICT (name) DO NOTHING;

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename         VARCHAR(500) NOT NULL,
    file_type        VARCHAR(20) NOT NULL,
    checksum         VARCHAR(64) NOT NULL UNIQUE,
    collection_id    UUID REFERENCES collections(id) ON DELETE CASCADE,
    sensitivity_tier VARCHAR(20) NOT NULL DEFAULT 'public',
    chunk_count      INTEGER NOT NULL DEFAULT 0,
    file_size        BIGINT NOT NULL,
    ingested_at      TIMESTAMPTZ DEFAULT now(),
    ingested_by      VARCHAR(255) DEFAULT 'system'
);
CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);

-- Ingestion Jobs
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path       TEXT NOT NULL,
    file_type       VARCHAR(20) NOT NULL,
    checksum        VARCHAR(64) NOT NULL,
    file_size       BIGINT NOT NULL,
    collection_id   UUID REFERENCES collections(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',
    retry_count     INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs(status);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username     VARCHAR(255) UNIQUE NOT NULL,
    clearance    VARCHAR(20) NOT NULL DEFAULT 'public',
    api_key_hash VARCHAR(255) NOT NULL,
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id),
    query_text          TEXT NOT NULL,
    collection_name     VARCHAR(255),
    user_clearance      VARCHAR(20) NOT NULL,
    chunks_retrieved    INTEGER NOT NULL,
    chunks_redacted     INTEGER NOT NULL,
    chunk_ids_returned  UUID[] NOT NULL DEFAULT '{}',
    chunk_ids_redacted  UUID[] NOT NULL DEFAULT '{}',
    response_summary    TEXT,
    query_duration_ms   FLOAT,
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

-- Schema migrations tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    description VARCHAR(255),
    applied_at  TIMESTAMPTZ DEFAULT now()
);

INSERT INTO schema_migrations (version, description)
VALUES (1, 'Initial schema')
ON CONFLICT (version) DO NOTHING;

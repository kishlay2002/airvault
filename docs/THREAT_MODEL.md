# VaultMind Threat Model

## Assets

1. **Document content** — ingested PDFs, audio transcripts, OCR'd images
2. **Vector embeddings** — semantic representations of document content
3. **User credentials** — API keys, clearance levels
4. **Audit trail** — query history, access patterns
5. **Model artifacts** — embedding model weights

## Threat Matrix

| Threat | Impact | Mitigation | Status |
|--------|--------|-----------|--------|
| Unauthorized data access via API | HIGH | API key auth + bcrypt hashing, clearance-based retrieval filtering | Implemented |
| Information leakage via relevance scores | MEDIUM | Filter at Qdrant query level, not post-retrieval | Implemented |
| Model tampering (supply chain) | HIGH | SHA-256 checksums + GPG signing of model artifacts | Implemented |
| Plaintext secrets in config | HIGH | All secrets via env vars; Vault integration for production | Implemented |
| Privilege escalation | HIGH | Clearance levels enforced at retrieval boundary, not API layer | Implemented |
| Audit log tampering | MEDIUM | Append-only audit table; no DELETE permissions for app user | Partial |
| Network eavesdropping | HIGH | mTLS between services (production); TLS for external API | Planned |
| Container escape | MEDIUM | Non-root containers, read-only filesystem, no shell in prod images | Implemented |
| Data exfiltration via egress | HIGH | Air-gapped deployment — no external network access | Implemented |
| Brute-force API key | MEDIUM | bcrypt (slow hash); rate limiting planned | Partial |

## Trust Boundaries

```
[External Client] --TLS--> [Query API] --mTLS--> [Qdrant / PostgreSQL / Redis]
                                |
                         [Auth Boundary]
                         API key → User → Clearance
                                |
                         [Data Boundary]
                         Clearance → Qdrant filter → Only allowed chunks
```

## Access Control Model

- **PUBLIC** — sees only public-tier chunks
- **INTERNAL** — sees public + internal
- **CONFIDENTIAL** — sees public + internal + confidential
- **RESTRICTED** — sees all tiers

Access is enforced at the **vector retrieval boundary** (Qdrant metadata filter), not at the API response layer. This means restricted chunks are never loaded into application memory for unauthorized users.

## Residual Risks

1. **Embedding inversion** — theoretically possible to reconstruct text from embeddings. Mitigated by access control on the vector DB itself.
2. **Side-channel via timing** — query latency may differ based on filtered chunk count. Low risk in practice.
3. **Admin CLI access** — anyone with CLI access and a valid API key can manage users. Restrict CLI access to authorized operators.

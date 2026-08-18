"""AirVault SDK — Quick Start Example.

Prerequisites:
    pip install vaultmind
    # Running Qdrant:  docker run -p 6333:6333 qdrant/qdrant
    # Running Postgres: docker run -p 5432:5432 -e POSTGRES_USER=vaultmind \
    #                   -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=vaultmind postgres:16-alpine

Usage:
    python examples/quickstart.py
"""

import asyncio
from airvault import AirVault, SensitivityTier


async def main():
    # 1. Initialize engine (connects to local Qdrant + PostgreSQL)
    engine = AirVault()

    # 2. Ingest a document
    result = await engine.ingest(
        "examples/sample_doc.txt",
        collection="demo",
        sensitivity=SensitivityTier.INTERNAL,
    )
    print(f"✓ Ingested: {result.filename} → {result.chunk_count} chunks ({result.sensitivity.value})")

    # 3. Query with access control
    results = await engine.query(
        "What are the key takeaways?",
        collection="demo",
        clearance=SensitivityTier.INTERNAL,
    )

    print(f"\n--- Query Results ({results.query_time_ms:.0f}ms) ---")
    print(f"Answer: {results.answer[:300]}")
    print(f"Citations: {results.chunks_retrieved}")
    print(f"Redacted: {results.chunks_redacted} chunks above clearance")

    for cite in results.citations:
        print(f"  [{cite.source}:{cite.page}] score={cite.score}")

    # 4. Try querying as a PUBLIC user (should redact INTERNAL chunks)
    public_results = await engine.query(
        "What are the key takeaways?",
        collection="demo",
        clearance=SensitivityTier.PUBLIC,
    )
    print(f"\n--- PUBLIC user results ---")
    print(f"Retrieved: {public_results.chunks_retrieved}")
    print(f"Redacted: {public_results.chunks_redacted} (access control enforced)")

    # 5. Check health
    health = await engine.health()
    print(f"\nHealth: {health.status}")
    for component, status in health.checks.items():
        print(f"  {component}: {status}")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())

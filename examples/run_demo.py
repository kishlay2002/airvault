"""AirVault — Full local demo.

Run this after starting Qdrant + PostgreSQL:
    python examples/run_demo.py
"""

import asyncio
from pathlib import Path
from airvault import AirVault, AirVaultConfig, SensitivityTier


async def main():
    config = AirVaultConfig(log_format="console")
    engine = AirVault(config)

    print("\n" + "=" * 60)
    print("  AirVault SDK — Local Demo")
    print("=" * 60)

    # ── Step 1: Health check ──
    print("\n[1] Health check...")
    health = await engine.health()
    print(f"    Status: {health.status}")
    for k, v in health.checks.items():
        print(f"    {k}: {v}")

    if health.status != "ok":
        print("\n    ⚠ Some dependencies are not reachable.")
        print("    Make sure Qdrant and PostgreSQL are running.")
        print("    See instructions in examples/README or run:")
        print("      docker run -d -p 6333:6333 qdrant/qdrant")
        print("      docker run -d -p 5432:5432 -e POSTGRES_USER=vaultmind \\")
        print("        -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=vaultmind postgres:16-alpine")
        await engine.close()
        return

    # ── Step 2: Ingest documents at different sensitivity levels ──
    print("\n[2] Ingesting documents...")

    # This file contains "INTERNAL ONLY" → auto-classified as INTERNAL
    sample = Path(__file__).parent / "sample_doc.txt"
    result1 = await engine.ingest(str(sample), collection="demo")
    print(f"    {result1.filename}: {result1.chunk_count} chunks, "
          f"sensitivity={result1.sensitivity.value} (auto-detected)")

    # Ingest some raw text at different tiers
    result2 = await engine.ingest_text(
        "The quarterly revenue was $12.3M, up 15% from last quarter. "
        "The new product launch exceeded expectations with 50,000 units sold. "
        "Market share increased to 23% in the enterprise segment. "
        "Customer retention rate held steady at 94%. "
        "The board approved a $5M investment in R&D for next quarter.",
        source_name="quarterly_report.txt",
        collection="demo",
        sensitivity=SensitivityTier.PUBLIC,
    )
    print(f"    {result2.filename}: {result2.chunk_count} chunks, "
          f"sensitivity={result2.sensitivity.value} (manual)")

    result3 = await engine.ingest_text(
        "CONFIDENTIAL: Project Aurora merger with Nexus Corp is on track. "
        "Due diligence reveals Nexus has $45M in recurring revenue. "
        "Proposed acquisition price is $200M with an earn-out of $50M. "
        "Legal team has flagged three pending patent disputes. "
        "Board vote scheduled for Q3. Do not discuss externally.",
        source_name="merger_notes.txt",
        collection="demo",
        sensitivity=SensitivityTier.CONFIDENTIAL,
    )
    print(f"    {result3.filename}: {result3.chunk_count} chunks, "
          f"sensitivity={result3.sensitivity.value} (manual)")

    # ── Step 3: Query as PUBLIC user ──
    print("\n[3] Querying as PUBLIC user: 'What is the revenue?'")
    public_results = await engine.query(
        "What is the revenue?",
        collection="demo",
        clearance=SensitivityTier.PUBLIC,
    )
    print(f"    Retrieved: {public_results.chunks_retrieved} chunks")
    print(f"    Redacted:  {public_results.chunks_redacted} chunks (above PUBLIC clearance)")
    for c in public_results.citations[:2]:
        print(f"    → [{c.source}] ({c.sensitivity.value}) score={c.score}")
        print(f"      {c.excerpt[:100]}...")

    # ── Step 4: Query as CONFIDENTIAL user (same query) ──
    print("\n[4] Querying as CONFIDENTIAL user: 'What is the revenue?'")
    conf_results = await engine.query(
        "What is the revenue?",
        collection="demo",
        clearance=SensitivityTier.CONFIDENTIAL,
    )
    print(f"    Retrieved: {conf_results.chunks_retrieved} chunks")
    print(f"    Redacted:  {conf_results.chunks_redacted} chunks")
    for c in conf_results.citations[:3]:
        print(f"    → [{c.source}] ({c.sensitivity.value}) score={c.score}")
        print(f"      {c.excerpt[:100]}...")

    # ── Step 5: Query about the merger as PUBLIC ──
    print("\n[5] Querying as PUBLIC user: 'Tell me about the merger'")
    merger_public = await engine.query(
        "Tell me about the merger",
        collection="demo",
        clearance=SensitivityTier.PUBLIC,
    )
    print(f"    Retrieved: {merger_public.chunks_retrieved} chunks")
    print(f"    Redacted:  {merger_public.chunks_redacted} chunks")
    if merger_public.chunks_redacted > 0:
        print(f"    ACCESS CONTROL WORKING: merger info hidden from PUBLIC user")

    # ── Step 6: Same query as CONFIDENTIAL ──
    print("\n[6] Querying as CONFIDENTIAL user: 'Tell me about the merger'")
    merger_conf = await engine.query(
        "Tell me about the merger",
        collection="demo",
        clearance=SensitivityTier.CONFIDENTIAL,
    )
    print(f"    Retrieved: {merger_conf.chunks_retrieved} chunks")
    print(f"    Redacted:  {merger_conf.chunks_redacted} chunks")
    for c in merger_conf.citations[:2]:
        print(f"    → [{c.source}] ({c.sensitivity.value}) score={c.score}")
        print(f"      {c.excerpt[:100]}...")

    # ── Step 7: List collections ──
    print("\n[7] Collections:")
    cols = await engine.list_collections()
    for col in cols:
        print(f"    {col.name}: {col.document_count} docs, {col.chunk_count} chunks")

    # ── Done ──
    print("\n" + "=" * 60)
    print("  Demo complete!")
    print("  Key takeaway: PUBLIC users NEVER see CONFIDENTIAL/INTERNAL chunks.")
    print("  Access control is enforced at the vector DB query level.")
    print("=" * 60 + "\n")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())

"""AirVault SDK — Access Control Demo.

Demonstrates compliance-aware retrieval: documents classified at different
sensitivity tiers are filtered based on the caller's clearance level.
"""

import asyncio
from airvault import AirVault, SensitivityTier


async def main():
    engine = AirVault()

    # Ingest documents at different sensitivity levels
    await engine.ingest_text(
        "Nuclear energy is a clean source of power that generates electricity "
        "using nuclear fission reactions. It produces minimal greenhouse gases.",
        source_name="nuclear_energy_basics.txt",
        collection="nuclear",
        sensitivity=SensitivityTier.PUBLIC,
    )

    await engine.ingest_text(
        "Nuclear launch code procedures require dual-key authorization from "
        "the President and Secretary of Defense. Codes are rotated daily.",
        source_name="launch_codes.txt",
        collection="nuclear",
        sensitivity=SensitivityTier.RESTRICTED,
    )

    print("=== Ingestion complete ===\n")

    # Query as PUBLIC user
    public_results = await engine.query(
        "Tell me about nuclear",
        collection="nuclear",
        clearance=SensitivityTier.PUBLIC,
    )
    print(f"PUBLIC user query:")
    print(f"  Chunks retrieved: {public_results.chunks_retrieved}")
    print(f"  Chunks redacted:  {public_results.chunks_redacted}")
    for c in public_results.citations:
        print(f"  → [{c.source}] {c.sensitivity.value}: {c.excerpt[:80]}...")

    print()

    # Query as RESTRICTED user
    restricted_results = await engine.query(
        "Tell me about nuclear",
        collection="nuclear",
        clearance=SensitivityTier.RESTRICTED,
    )
    print(f"RESTRICTED user query:")
    print(f"  Chunks retrieved: {restricted_results.chunks_retrieved}")
    print(f"  Chunks redacted:  {restricted_results.chunks_redacted}")
    for c in restricted_results.citations:
        print(f"  → [{c.source}] {c.sensitivity.value}: {c.excerpt[:80]}...")

    # Verify: PUBLIC user NEVER sees RESTRICTED chunks
    assert all(
        c.sensitivity == SensitivityTier.PUBLIC for c in public_results.citations
    ), "SECURITY VIOLATION: restricted chunks leaked to public user!"
    print("\n✓ Access control verified: restricted chunks never leak to public users")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
